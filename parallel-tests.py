#!/usr/bin/env python3
"""parallel-tests.py — experimental parallel runner for larch test harnesses.

Discovers tests by running `make -n test-harnesses` (single source of
truth — same list CI uses). Runs them in a thread pool of N workers,
captures per-test combined stdout+stderr, prints live PASS/FAIL progress
without interleaving, and dumps full output of failures at the end.

Threads (not processes) are used because each test is a `subprocess.run`
that releases the GIL during wait. Process pool would add fork overhead
without buying anything here.

Examples:
    python3 parallel-tests.py                       # default: 2 * cores
    python3 parallel-tests.py -j 1                  # serial baseline
    python3 parallel-tests.py -j 8                  # 8 workers
    python3 parallel-tests.py --sweep 1,2,4,8,16,32 # compare wall times
    python3 parallel-tests.py --verify-flakes       # re-run fails serially
    python3 parallel-tests.py --rerun-failed        # rerun last failures
    python3 parallel-tests.py --filter token        # subset by substring
    python3 parallel-tests.py --list                # just print test list
    python3 parallel-tests.py --shuffle             # randomize order

Test list overrides:
    Positional args (after flags) restrict to named tests, e.g.
        python3 parallel-tests.py test-token-cost test-larch-log

Auxiliary outputs (written to current dir):
    .parallel-tests-last-failures.txt   names of last-run failed tests
    .parallel-tests-last-output/<name>.log   captured output of each test
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shlex
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent
LAST_FAILURES_FILE = REPO_ROOT / ".parallel-tests-last-failures.txt"
LAST_OUTPUT_DIR = REPO_ROOT / ".parallel-tests-last-output"
TIMINGS_FILE = REPO_ROOT / ".parallel-tests-timings.json"
TIMING_LINE_RE = re.compile(r"^LARCH_HARNESS_TIMING\t([^\t]+)\t([0-9.]+)s\s*$")


def load_timings() -> Dict[str, float]:
    if not TIMINGS_FILE.exists():
        return {}
    try:
        return {k: float(v) for k, v in json.loads(TIMINGS_FILE.read_text()).items()}
    except Exception:
        return {}


def save_timings(results: List[dict]) -> None:
    """Merge fresh PASS-only timings into the cache. Failures don't update timings."""
    existing = load_timings()
    for r in results:
        if r["rc"] != 0:
            continue
        t = r.get("inner_timing") or r.get("wall") or 0.0
        if t > 0:
            existing[r["name"]] = t
    TIMINGS_FILE.write_text(json.dumps(existing, indent=2, sort_keys=True))


def order_by_lpt(tests: List[Tuple[str, str]], timings: Dict[str, float]) -> List[Tuple[str, str]]:
    """Sort tests longest-first by cached timing. Unknown-timing tests sort last (FIFO)."""
    if not timings:
        return tests
    known = [(t, timings[t[0]]) for t in tests if t[0] in timings]
    unknown = [t for t in tests if t[0] not in timings]
    known.sort(key=lambda x: x[1], reverse=True)
    return [t for (t, _) in known] + unknown


def detect_cores() -> int:
    """Logical core count, respecting Linux affinity if available."""
    try:
        return len(os.sched_getaffinity(0))  # Linux, respects taskset/cgroups
    except AttributeError:
        return os.cpu_count() or 1  # macOS / older platforms


def _extract_test_name(line: str) -> Optional[str]:
    """Parse a `make -n test-harnesses` recipe line into a test name.

    Three patterns observed:
      1. `bash scripts/harness-timer.sh <name> <inner>`            (most tests)
      2. `env ... bash scripts/harness-timer.sh <name> <inner>`    (env-prefixed)
      3. `bash scripts/<test-NAME>.sh`                              (legacy, no timer)
    """
    parts = shlex.split(line)
    if not parts:
        return None
    # Skip env-prefix tokens like "env -u FOO=bar" or "VAR=val" until we hit `bash`.
    i = 0
    while i < len(parts) and parts[i] != "bash":
        # tokens that can precede `bash`: `env`, `-u`, `FOO=bar`, etc.
        i += 1
    if i >= len(parts) - 1:
        return None
    # Now parts[i] == 'bash', parts[i+1] == <script>
    script = parts[i + 1]
    if script.endswith("scripts/harness-timer.sh") and i + 2 < len(parts):
        return parts[i + 2]
    # Direct invocation: bash scripts/test-foo.sh → name = "test-foo"
    base = os.path.basename(script)
    if base.startswith("test-") and base.endswith(".sh"):
        return base[: -len(".sh")]
    return None


def discover_tests() -> List[Tuple[str, str]]:
    """Return list of (test_name, command_line) tuples from `make -n test-harnesses`."""
    res = subprocess.run(
        ["make", "-n", "test-harnesses"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        sys.exit(
            f"ERROR: `make -n test-harnesses` failed (exit {res.returncode}):\n"
            f"{res.stderr}"
        )
    tests: List[Tuple[str, str]] = []
    seen = set()
    skipped = 0
    for line in res.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("make"):
            continue
        name = _extract_test_name(line)
        if name is None:
            skipped += 1
            continue
        if name in seen:
            continue
        seen.add(name)
        tests.append((name, line))
    if skipped:
        print(f"# warning: skipped {skipped} unrecognized recipe lines", file=sys.stderr)
    return tests


def filter_tests(
    tests: List[Tuple[str, str]],
    positional: List[str],
    substring: Optional[str],
    rerun_failed: bool,
) -> List[Tuple[str, str]]:
    if rerun_failed:
        if not LAST_FAILURES_FILE.exists():
            sys.exit(f"ERROR: --rerun-failed but {LAST_FAILURES_FILE} not found.")
        wanted = {
            line.strip()
            for line in LAST_FAILURES_FILE.read_text().splitlines()
            if line.strip()
        }
        if not wanted:
            sys.exit(f"ERROR: {LAST_FAILURES_FILE} is empty.")
        tests = [t for t in tests if t[0] in wanted]
    if positional:
        wanted = set(positional)
        tests = [t for t in tests if t[0] in wanted]
        missing = wanted - {t[0] for t in tests}
        if missing:
            sys.exit(f"ERROR: tests not found in make graph: {sorted(missing)}")
    if substring:
        tests = [t for t in tests if substring in t[0]]
    return tests


class Runner:
    def __init__(
        self,
        workers: int,
        timeout: Optional[float],
        quiet: bool,
        output_dir: Path,
    ) -> None:
        self.workers = workers
        self.timeout = timeout
        self.quiet = quiet
        self.output_dir = output_dir
        self.print_lock = threading.Lock()
        self.completed = 0
        self.total = 0
        self.start_wall = 0.0

    def _run_one(self, name: str, cmd: str) -> dict:
        out_path = self.output_dir / f"{name}.log"
        t0 = time.monotonic()
        output = ""
        rc = 0
        timed_out = False
        # start_new_session=True puts the child (and its descendants) into a
        # fresh process group so we can SIGKILL the whole tree on timeout.
        # Without this, proc.kill() only killed the outer `bash -c`, leaving
        # the test's spawned bash/python/git children running as orphans —
        # which then competed for CPU with the *next* test we scheduled.
        proc = subprocess.Popen(
            ["bash", "-c", cmd],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        try:
            raw, _ = proc.communicate(timeout=self.timeout)
            output = raw or ""
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
            try:
                raw, _ = proc.communicate(timeout=5)
                output = raw or ""
            except subprocess.TimeoutExpired:
                output = ""
            output += f"\n[parallel-tests.py] TIMEOUT after {self.timeout}s — process group killed\n"
            rc = 124
        except Exception as exc:  # any other crash inside worker is non-fatal
            output += f"\n[parallel-tests.py] worker exception: {exc!r}\n"
            rc = 125
        wall = time.monotonic() - t0

        # Parse the harness-timer line for the test's own measured runtime.
        # Falls back to the wall-clock if the line is missing.
        inner_timing: Optional[float] = None
        for line in output.splitlines():
            m = TIMING_LINE_RE.match(line)
            if m and m.group(1) == name:
                inner_timing = float(m.group(2))
                break

        out_path.write_text(output)

        return {
            "name": name,
            "rc": rc,
            "wall": wall,
            "inner_timing": inner_timing,
            "timed_out": timed_out,
            "output": output,
            "log_path": out_path,
        }

    def _on_complete(self, result: dict) -> None:
        with self.print_lock:
            self.completed += 1
            n = self.completed
            tot = self.total
            elapsed = time.monotonic() - self.start_wall
            status = "PASS" if result["rc"] == 0 else "FAIL"
            tag = "TIMEOUT" if result["timed_out"] else status
            name = result["name"]
            wall = result["wall"]
            if not self.quiet:
                print(
                    f"[{n:>3d}/{tot}] {tag:<7} {name:<60} ({wall:5.2f}s, elapsed {elapsed:6.1f}s)",
                    flush=True,
                )

    def run(self, tests: List[Tuple[str, str]]) -> List[dict]:
        self.total = len(tests)
        self.completed = 0
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Wipe stale logs so we don't confuse this run with prior runs.
        for old in self.output_dir.glob("*.log"):
            try:
                old.unlink()
            except OSError:
                pass

        self.start_wall = time.monotonic()
        results: List[dict] = []
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {pool.submit(self._run_one, name, cmd): name for name, cmd in tests}
            for fut in as_completed(futures):
                name = futures[fut]
                try:
                    r = fut.result()
                except Exception as exc:
                    # Defense in depth — _run_one already catches, but if anything
                    # bubbles up still, record it as a failure and keep going.
                    r = {
                        "name": name,
                        "rc": 126,
                        "wall": 0.0,
                        "inner_timing": None,
                        "timed_out": False,
                        "output": f"[parallel-tests.py] future raised: {exc!r}\n",
                        "log_path": self.output_dir / f"{name}.log",
                    }
                    r["log_path"].write_text(r["output"])
                results.append(r)
                self._on_complete(r)
        return results


def print_summary(results: List[dict], wall: float, workers: int) -> List[str]:
    failed = [r for r in results if r["rc"] != 0]
    passed = [r for r in results if r["rc"] == 0]

    sum_inner = sum((r["inner_timing"] or r["wall"]) for r in results)
    speedup = sum_inner / wall if wall > 0 else 0.0

    print()
    print("=" * 78)
    print(f"workers:       {workers}")
    print(f"tests:         {len(results)}")
    print(f"passed:        {len(passed)}")
    print(f"failed:        {len(failed)}")
    print(f"wall:          {wall:.2f}s")
    print(f"sum (serial):  {sum_inner:.2f}s  (sum of per-test runtimes)")
    print(f"speedup:       {speedup:.2f}x  (sum/wall, theoretical max = workers)")
    print(f"efficiency:    {(100.0 * speedup / workers if workers else 0):.0f}%  (speedup / workers)")
    print()

    # Slowest 10 tests by inner timing (or wall as fallback).
    slowest = sorted(
        results,
        key=lambda r: (r["inner_timing"] or r["wall"]),
        reverse=True,
    )[:10]
    print("slowest 10 tests:")
    for r in slowest:
        t = r["inner_timing"] or r["wall"]
        print(f"    {t:6.2f}s  {r['name']}")
    print()

    if failed:
        print("=" * 78)
        print(f"FAILURES ({len(failed)}):")
        for r in failed:
            print()
            print("-" * 78)
            tag = "TIMEOUT" if r["timed_out"] else f"FAIL rc={r['rc']}"
            print(f"{tag}: {r['name']}   (log: {r['log_path']})")
            print("-" * 78)
            # Tail the captured output to keep terminal manageable.
            tail = r["output"].splitlines()[-80:]
            for line in tail:
                print(line)
        print()
    return [r["name"] for r in failed]


def write_failures(failed_names: List[str]) -> None:
    if failed_names:
        LAST_FAILURES_FILE.write_text("\n".join(failed_names) + "\n")
    elif LAST_FAILURES_FILE.exists():
        LAST_FAILURES_FILE.unlink()


def verify_flakes(failed_names: List[str], tests: List[Tuple[str, str]]) -> None:
    """Re-run previously-failed tests serially to attribute parallel-only flakes."""
    if not failed_names:
        return
    print()
    print("=" * 78)
    print(f"Re-running {len(failed_names)} failed test(s) SERIALLY to check for parallel-only flakes...")
    print("=" * 78)
    name_to_cmd = dict(tests)
    serial_runner = Runner(workers=1, timeout=None, quiet=False, output_dir=LAST_OUTPUT_DIR / "verify")
    serial_results = serial_runner.run([(n, name_to_cmd[n]) for n in failed_names if n in name_to_cmd])
    serial_failed = [r["name"] for r in serial_results if r["rc"] != 0]
    serial_passed_now = [n for n in failed_names if n not in serial_failed]
    print()
    print("verify-flakes summary:")
    print(f"    failed in parallel AND serial: {len(serial_failed)}  (real failures)")
    print(f"    failed in parallel, PASS serial: {len(serial_passed_now)}  (parallel-only flakes)")
    if serial_passed_now:
        print()
        print("PARALLEL-ONLY FLAKES (passed when re-run serially):")
        for n in sorted(serial_passed_now):
            print(f"    {n}")


def sweep(values: List[int], tests: List[Tuple[str, str]], timeout: Optional[float], quiet: bool) -> None:
    """Run the suite multiple times at different worker counts; print a comparison table."""
    rows = []
    # Freeze LPT order at sweep start so all N values run the same sequence.
    timings_snapshot = load_timings()
    if timings_snapshot:
        tests = order_by_lpt(tests, timings_snapshot)
        print(f"# sweep: LPT ordering applied from {len(timings_snapshot)} cached timings")
    for n in values:
        print()
        print("#" * 78)
        print(f"# sweep: -j {n}  (tests={len(tests)}, timeout={timeout}s)")
        print("#" * 78)
        runner = Runner(workers=n, timeout=timeout, quiet=quiet, output_dir=LAST_OUTPUT_DIR / f"sweep-{n}")
        t0 = time.monotonic()
        results = runner.run(tests)
        wall = time.monotonic() - t0
        failed = sum(1 for r in results if r["rc"] != 0)
        sum_inner = sum((r["inner_timing"] or r["wall"]) for r in results)
        speedup = sum_inner / wall if wall > 0 else 0.0
        eff = 100.0 * speedup / n if n else 0.0
        rows.append((n, wall, sum_inner, speedup, eff, failed))
        # Save fresh timings from this run so the sweep's later iterations
        # use up-to-date data when --no-lpt isn't passed. (LPT order itself
        # is frozen above, but the timing cache improves future invocations.)
        save_timings(results)

    print()
    print("=" * 78)
    print("SWEEP RESULTS")
    print("=" * 78)
    print(f"{'workers':>8}  {'wall (s)':>10}  {'sum (s)':>10}  {'speedup':>8}  {'eff (%)':>8}  {'failed':>7}")
    for n, wall, sum_inner, speedup, eff, failed in rows:
        print(f"{n:>8d}  {wall:>10.2f}  {sum_inner:>10.2f}  {speedup:>8.2f}  {eff:>8.0f}  {failed:>7d}")


def parse_args(argv: List[str]) -> argparse.Namespace:
    cores = detect_cores()
    p = argparse.ArgumentParser(description="Experimental parallel test runner.")
    p.add_argument(
        "-j", "--jobs", default=str(2 * cores),
        help=f"Number of parallel workers (default: 2*cores = {2 * cores}). Use 'auto' = 2*cores.",
    )
    p.add_argument("--filter", default=None, help="Only run tests whose name contains this substring.")
    p.add_argument("--shuffle", action="store_true", help="Shuffle test order before running.")
    p.add_argument("--seed", type=int, default=None, help="Seed for --shuffle (reproducibility).")
    p.add_argument("--no-lpt", action="store_true",
                   help="Disable Longest-Processing-Time ordering (default: on if timings cached). "
                        "--shuffle implies --no-lpt.")
    p.add_argument("--timeout", type=float, default=300.0, help="Per-test timeout in seconds (default 300).")
    p.add_argument("--list", action="store_true", help="Print the resolved test list and exit.")
    p.add_argument("--dry-run", action="store_true", help="Print full commands that would run, then exit.")
    p.add_argument("--sweep", default=None,
                   help="Comma-separated worker counts to compare, e.g. '1,2,4,8,16'.")
    p.add_argument("--verify-flakes", action="store_true",
                   help="After parallel run, re-run failures serially to attribute parallel-only flakes.")
    p.add_argument("--rerun-failed", action="store_true",
                   help="Only run tests listed in .parallel-tests-last-failures.txt from previous run.")
    p.add_argument("--quiet", action="store_true", help="Suppress per-test progress lines (still prints summary).")
    p.add_argument("tests", nargs="*", help="Optional positional list of test names to restrict to.")
    args = p.parse_args(argv)
    if args.jobs == "auto":
        args.jobs = 2 * cores
    else:
        try:
            args.jobs = int(args.jobs)
        except ValueError:
            p.error(f"--jobs must be int or 'auto', got: {args.jobs!r}")
    if args.jobs < 1:
        p.error(f"--jobs must be >= 1, got: {args.jobs}")
    return args


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    cores = detect_cores()
    print(f"# detected cores: {cores}   default workers (2*cores): {2 * cores}")

    tests = discover_tests()
    print(f"# discovered {len(tests)} tests via `make -n test-harnesses`")

    tests = filter_tests(
        tests,
        positional=args.tests,
        substring=args.filter,
        rerun_failed=args.rerun_failed,
    )
    print(f"# selected  {len(tests)} tests after filtering")

    if args.shuffle:
        if args.seed is not None:
            random.seed(args.seed)
        random.shuffle(tests)
    elif not args.no_lpt:
        timings = load_timings()
        if timings:
            tests = order_by_lpt(tests, timings)
            print(f"# LPT ordering applied ({len(timings)} cached timings)")

    if args.list:
        for name, _ in tests:
            print(name)
        return 0
    if args.dry_run:
        for name, cmd in tests:
            print(f"{name}\t{cmd}")
        return 0

    if not tests:
        print("# no tests to run")
        return 0

    if args.sweep:
        try:
            values = [int(v.strip()) for v in args.sweep.split(",") if v.strip()]
        except ValueError:
            sys.exit(f"ERROR: --sweep must be comma-separated ints, got: {args.sweep!r}")
        if not values:
            sys.exit("ERROR: --sweep needs at least one value.")
        sweep(values, tests, args.timeout, args.quiet)
        return 0

    runner = Runner(
        workers=args.jobs,
        timeout=args.timeout,
        quiet=args.quiet,
        output_dir=LAST_OUTPUT_DIR,
    )
    t0 = time.monotonic()
    results = runner.run(tests)
    wall = time.monotonic() - t0

    failed_names = print_summary(results, wall, args.jobs)
    write_failures(failed_names)
    save_timings(results)

    if args.verify_flakes and failed_names:
        verify_flakes(failed_names, tests)

    return 1 if failed_names else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
