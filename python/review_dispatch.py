# pyright: reportUnusedCallResult=false
"""Leaf dispatch helpers for reviewer waiting, diff routing, and collector logs."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable, Sequence

import agents
import logging_util

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATORS_TSV = REPO_ROOT / "scripts" / "generators.tsv"
DIFF_MODES = {"generic", "docs-only", "test-only", "generated-only"}
WAIT_DEFAULT_TIMEOUT = 1860
WAIT_DEFAULT_POLL_INTERVAL = "5"
SUSPEND_REFUND_SECONDS = 60
GENERATORS_TSV_COLUMNS = 2


@dataclass(frozen=True)
class WaitClock:
    """Injectable clock seam for wait-reviewers tests."""

    now: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep


def _usage_wait() -> str:
    return "Usage: wait-for-reviewers.sh [--timeout SECONDS] <sentinel.done> [sentinel2.done ...]"


def _validate_positive_int(*, raw: str, flag: str) -> int | None:
    if not raw or not raw.isdigit():
        print(f"Error: {flag} value must be a positive integer, got '{raw}'", file=sys.stderr)
        return None
    value = int(raw, 10)
    if value < 1:
        print(f"Error: {flag} value must be a positive integer, got '{raw}'", file=sys.stderr)
        return None
    return value


def _parse_wait_args(argv: Sequence[str]) -> tuple[int, list[str]] | None:
    timeout_raw = str(WAIT_DEFAULT_TIMEOUT)
    sentinels: list[str] = []
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg == "--timeout":
            if idx + 1 >= len(argv):
                print("--timeout requires a value", file=sys.stderr)
                return None
            timeout_raw = argv[idx + 1]
            idx += 2
        elif arg == "--help":
            print(_usage_wait(), file=sys.stderr)
            raise SystemExit(0)
        elif arg.startswith("-"):
            print(f"Unknown option: {arg}", file=sys.stderr)
            print(_usage_wait(), file=sys.stderr)
            return None
        else:
            sentinels = list(argv[idx:])
            break
    timeout = _validate_positive_int(raw=timeout_raw, flag="--timeout")
    if timeout is None:
        return None
    if not sentinels:
        print("ERROR: at least one sentinel file path is required", file=sys.stderr)
        print(_usage_wait(), file=sys.stderr)
        return None
    return timeout, sentinels


def _parse_poll_interval(raw: str) -> float | None:
    if not raw or raw in {".", "0", "0.", "0.0", "0.00", "0.000"}:
        return None
    if raw.count(".") > 1:
        return None
    if not re.fullmatch(r"[0-9.]+", raw):
        return None
    if "." not in raw and int(raw, 10) < 1:
        return None
    value = float(raw)
    if value <= 0:
        return None
    return value


def wait_max_polls(*, timeout: int, poll_interval: float) -> int:
    max_polls = int((timeout + poll_interval - 0.001) / poll_interval)
    return max(1, max_polls)


def _sentinel_name(path: str) -> str:
    base = Path(path).name
    return base.removesuffix(".done")


def _read_exit_code(path: str) -> str:
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "unknown"
    code = "".join(text.split())
    return code if code.isdigit() and code else "unknown"


def wait_reviewers(
    sentinels: Sequence[str],
    *,
    timeout: int = WAIT_DEFAULT_TIMEOUT,
    poll_interval: float | None = None,
    clock: WaitClock | None = None,
    emit_fn: Callable[[str], None] = logging_util.emit,
    diagnostic_fn: Callable[[str], None] = logging_util.diagnostic,
) -> int:
    """Wait for reviewer sentinel files and emit DONE/TIMEOUT rows."""
    if poll_interval is None:
        raw = os.environ.get("WAIT_FOR_REVIEWERS_POLL_INTERVAL", WAIT_DEFAULT_POLL_INTERVAL)
        parsed = _parse_poll_interval(raw)
        if parsed is None:
            diagnostic_fn(f"Error: WAIT_FOR_REVIEWERS_POLL_INTERVAL must be a positive number, got '{raw}'")
            return 1
        poll_interval = parsed
    clock = clock or WaitClock()
    max_polls = wait_max_polls(timeout=timeout, poll_interval=poll_interval)
    total = len(sentinels)
    found: dict[int, str] = {}
    found_count = 0
    checks = 0
    suspend_refunds = 0
    last_progress_minute = 0
    start = clock.now()

    def check_sentinels() -> None:
        nonlocal found_count
        for idx, sentinel in enumerate(sentinels, start=1):
            if idx in found:
                continue
            if Path(sentinel).is_file():
                exit_code = _read_exit_code(sentinel)
                found[idx] = exit_code
                found_count += 1
                diagnostic_fn(f"\n✓ {_sentinel_name(sentinel)}: exit={exit_code}")

    check_sentinels()
    while found_count < total and checks < max_polls:
        iter_start = clock.now()
        diagnostic_fn(".")
        checks += 1
        elapsed_minute = int((clock.now() - start) // 60)
        if elapsed_minute >= 1 and elapsed_minute != last_progress_minute:
            diagnostic_fn(f"\n⏳ Waiting: {elapsed_minute}m elapsed, {checks} checks, {found_count}/{total} done")
            last_progress_minute = elapsed_minute
        clock.sleep(poll_interval)
        check_sentinels()
        iter_delta = int(clock.now() - iter_start)
        if iter_delta > SUSPEND_REFUND_SECONDS:
            diagnostic_fn(f"\n⚠ suspend detected — iteration took {iter_delta}s, not counting toward poll budget")
            if suspend_refunds < max_polls:
                checks -= 1
                suspend_refunds += 1

    elapsed = int(clock.now() - start)
    diagnostic_fn("\n")
    timed_out = 0
    for idx, sentinel in enumerate(sentinels, start=1):
        name = _sentinel_name(sentinel)
        if idx in found:
            emit_fn(f"DONE {idx} {name}: exit={found[idx]}")
        else:
            emit_fn(f"TIMEOUT {idx} {name}")
            timed_out += 1
    if timed_out:
        diagnostic_fn(f"⚠ {timed_out}/{total} reviewer(s) timed out after {timeout} seconds")
    else:
        diagnostic_fn(f"✓ All {total} reviewer(s) completed in {elapsed}s")
    return 0


def wait_reviewers_main(argv: list[str] | None = None) -> int:
    args_list = sys.argv[1:] if argv is None else argv
    try:
        parsed = _parse_wait_args(args_list)
    except SystemExit as exc:
        return int(exc.code or 0)
    if parsed is None:
        return 1
    timeout, sentinels = parsed
    raw_poll = os.environ.get("WAIT_FOR_REVIEWERS_POLL_INTERVAL", WAIT_DEFAULT_POLL_INTERVAL)
    poll_interval = _parse_poll_interval(raw_poll)
    if poll_interval is None:
        print(f"Error: WAIT_FOR_REVIEWERS_POLL_INTERVAL must be a positive number, got '{raw_poll}'", file=sys.stderr)
        return 1
    logging_util.quiet_init(argv0="wait-for-reviewers.sh")
    return wait_reviewers(sentinels, timeout=timeout, poll_interval=poll_interval)


def _generated_paths(tsv_path: Path | None = None) -> set[str]:
    path = tsv_path if tsv_path is not None else GENERATORS_TSV
    out: set[str] = set()
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) == GENERATORS_TSV_COLUMNS and parts[1]:
                out.add(parts[1])
    except OSError:
        return set()
    return out


def _classify_path(*, path: str, generated: set[str]) -> str:
    if not path or path.startswith("/") or ".." in path:
        return "generic"
    if path in generated:
        return "generated-only"
    base = Path(path).name
    test_patterns = (
        r"scripts/test-.*\.(sh|py)",
        r"skills/[^/]+/scripts/test-.*\.sh",
        r"test_.*\.(sh|py|go)",
        r".*_test\.(sh|py|go)",
        r".*\.test\.(sh|py|go)",
    )
    if any(re.fullmatch(pattern, path) for pattern in test_patterns[:2]):
        return "test-only"
    if re.fullmatch(r"[^/]+/tests/[^/]+\.(sh|py|go|bats)$", path) or re.fullmatch(
        r"[^/]+/test/[^/]+\.(sh|py|go|bats)$", path
    ):
        return "test-only"
    if any(re.fullmatch(pattern, base) for pattern in test_patterns[2:]) or base.endswith(".bats"):
        return "test-only"
    if (
        re.fullmatch(r"docs/[^/]+\.(md|txt|rst|adoc)$", path)
        or re.fullmatch(r"scripts/[^/]+\.md$", path)
        or path in {"README.md", "SECURITY.md", "AGENTS.md", "CLAUDE.md", "KARPATHY_CLAUDE.md"}
    ):
        return "docs-only"
    return "generic"


def classify_diff(path: str) -> str:
    """Classify a git diff file by changed path mode. Never emits output."""
    try:
        diff_path = Path(path)
        if not diff_path.is_file():
            return "generic"
        generated = _generated_paths()
        mode = ""
        seen = False
        header_re = re.compile(r"^diff --git a/([^\s]+) b/([^\s]+)$")
        with diff_path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.startswith("diff --git "):
                    continue
                seen = True
                match = header_re.match(line.rstrip("\n"))
                if match is None:
                    return "generic"
                old_path, new_path = match.groups()
                old_mode = _classify_path(path=old_path, generated=generated)
                new_mode = _classify_path(path=new_path, generated=generated)
                if old_mode != new_mode or old_mode == "generic":
                    return "generic"
                if not mode:
                    mode = old_mode
                elif mode != old_mode:
                    return "generic"
        if not seen or not mode:
            return "generic"
        return mode if mode in DIFF_MODES else "generic"
    except Exception:
        return "generic"


def classify_diff_main(argv: list[str] | None = None) -> int:
    args_list = sys.argv[1:] if argv is None else argv
    if len(args_list) != 1:
        print("classify-diff-mode.sh: expected exactly one diff file path", file=sys.stderr)
        return 2
    diff_file = args_list[0]
    if not Path(diff_file).is_file():
        print(f"classify-diff-mode.sh: diff file not found: {diff_file}", file=sys.stderr)
        return 2
    logging_util.quiet_init(argv0="classify-diff-mode.sh")
    logging_util.emit_kv("DIFF_MODE", classify_diff(diff_file))
    return 0


def gather_branch_context(output_dir: str) -> tuple[str, str, str, int]:
    out = Path(output_dir)
    diff_file = out / "diff.txt"
    file_list_file = out / "file-list.txt"
    commit_log_file = out / "commit-log.txt"
    merge = subprocess.run(["git", "merge-base", "HEAD", "main"], check=False, capture_output=True, text=True)  # noqa: S607
    if merge.returncode != 0:
        raise RuntimeError((merge.stderr or merge.stdout or "git merge-base failed").strip())
    merge_base = merge.stdout.strip()
    commands = [
        (["git", "diff", "-U20", f"{merge_base}...HEAD", "--", ".", ":(exclude)larch-logs/**"], diff_file),
        (["git", "diff", f"{merge_base}...HEAD", "--name-only", "--", ".", ":(exclude)larch-logs/**"], file_list_file),
        (["git", "log", f"{merge_base}..HEAD", "--oneline", "--", ".", ":(exclude)larch-logs/**"], commit_log_file),
    ]
    for cmd, target in commands:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or f"git command failed: {' '.join(cmd)}").strip())
        target.write_text(result.stdout, encoding="utf-8")
    commit_count = len(commit_log_file.read_text(encoding="utf-8", errors="replace").splitlines())
    return str(diff_file), str(file_list_file), str(commit_log_file), commit_count


def gather_branch_context_main(argv: list[str] | None = None) -> int:
    args_list = sys.argv[1:] if argv is None else argv
    output_dir = ""
    idx = 0
    while idx < len(args_list):
        arg = args_list[idx]
        if arg == "--output-dir":
            if idx + 1 >= len(args_list):
                print("--output-dir requires a value", file=sys.stderr)
                return 1
            output_dir = args_list[idx + 1]
            idx += 2
        elif arg == "--help":
            print("Usage: gather-branch-context.sh --output-dir <path>", file=sys.stderr)
            return 0
        else:
            print(f"Unknown option: {arg}", file=sys.stderr)
            print("Usage: gather-branch-context.sh --output-dir <path>", file=sys.stderr)
            return 1
    if not output_dir:
        print("ERROR: --output-dir is required", file=sys.stderr)
        print("Usage: gather-branch-context.sh --output-dir <path>", file=sys.stderr)
        return 1
    if not Path(output_dir).is_dir():
        print(f"ERROR: output directory does not exist: {output_dir}", file=sys.stderr)
        return 1
    logging_util.quiet_init(argv0="gather-branch-context.sh")
    try:
        diff_file, file_list_file, commit_log_file, commit_count = gather_branch_context(output_dir)
    except Exception as exc:
        logging_util.diagnostic(f"gather-branch-context.sh: {exc}")
        return 1
    logging_util.emit_kv("DIFF_FILE", diff_file)
    logging_util.emit_kv("FILE_LIST_FILE", file_list_file)
    logging_util.emit_kv("COMMIT_LOG_FILE", commit_log_file)
    logging_util.emit_kv("COMMIT_COUNT", str(commit_count))
    return 0


def render_failed_agent_stderr_tail(path: str) -> str:
    return agents.render_failed_agent_stderr_tail(Path(path))


def _redacted_launch_stderr_body(path: str) -> str:
    rendered = render_failed_agent_stderr_tail(path)
    if rendered:
        return rendered
    return f"(launcher stderr redaction unavailable or empty: {path})"


def _dump_section(*, header: str, path: str) -> str:
    parts = [f"## {header}\n\n"]
    if not path:
        parts.append("(no path provided)\n\n")
    else:
        p = Path(path)
        if not p.exists():
            parts.append(f"(file missing: {path})\n\n")
        elif p.stat().st_size <= 0:
            parts.append(f"(empty: {path})\n\n")
        elif path.endswith((".launch-stderr", ".stderr-tail")):
            parts.append(_redacted_launch_stderr_body(path))
            parts.append("\n\n")
        else:
            parts.append(p.read_text(encoding="utf-8", errors="replace"))
            parts.append("\n")
    return "".join(parts)


def compose_collector_failure_log(*, reviewer_file: str, structured_record: str, output: str) -> None:
    body = ["## Structured collector record\n\n", structured_record, "\n\n"]
    body.append(_dump_section(header=f"Reviewer output ({reviewer_file})", path=reviewer_file))
    if reviewer_file:
        body.append(_dump_section(header=f"Reviewer stderr ({reviewer_file}.diag)", path=f"{reviewer_file}.diag"))
        body.append(_dump_section(header=f"Failed-agent stderr tail ({reviewer_file}.stderr-tail)", path=f"{reviewer_file}.stderr-tail"))
        body.append(_dump_section(header=f"Launcher stderr ({reviewer_file}.launch-stderr)", path=f"{reviewer_file}.launch-stderr"))
    text = "".join(body)
    if not text.strip():
        text = "collector failure log unavailable\n"
    target = Path(output)
    fd, tmp = tempfile.mkstemp(prefix=".compose-collector-failure-log.", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        Path(tmp).replace(target)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def compose_collector_failure_log_main(argv: list[str] | None = None) -> int:
    args_list = sys.argv[1:] if argv is None else argv
    reviewer_file = ""
    structured_record = ""
    output = ""
    idx = 0
    while idx < len(args_list):
        arg = args_list[idx]
        if arg == "--reviewer-file":
            if idx + 1 >= len(args_list):
                print("--reviewer-file requires a value", file=sys.stderr)
                return 2
            reviewer_file = args_list[idx + 1]
            idx += 2
        elif arg == "--structured-record":
            if idx + 1 >= len(args_list):
                print("--structured-record requires a value", file=sys.stderr)
                return 2
            structured_record = args_list[idx + 1]
            idx += 2
        elif arg == "--output":
            if idx + 1 >= len(args_list):
                print("--output requires a value", file=sys.stderr)
                return 2
            output = args_list[idx + 1]
            idx += 2
        else:
            print(f"compose-collector-failure-log.sh: unknown flag: {arg}", file=sys.stderr)
            return 2
    if not structured_record:
        print("--structured-record is required and non-empty", file=sys.stderr)
        return 2
    if not output:
        print("--output is required", file=sys.stderr)
        return 2
    parent = Path(output).parent
    if not parent.is_dir():
        print(f"--output parent directory missing: {parent}", file=sys.stderr)
        return 2
    logging_util.quiet_init(argv0="compose-collector-failure-log.sh")
    try:
        compose_collector_failure_log(reviewer_file=reviewer_file, structured_record=structured_record, output=output)
    except Exception as exc:
        logging_util.diagnostic(f"compose-collector-failure-log.sh: {exc}")
        return 1
    return 0
