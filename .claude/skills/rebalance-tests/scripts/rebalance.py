#!/usr/bin/env python3
"""Rebalance CI test shards and verify the result.

Run from the repository root::

    python3 .claude/skills/rebalance-tests/scripts/rebalance.py [flags]

See .claude/skills/rebalance-tests/SKILL.md for full documentation.

NOTE: the final ``pr_merge`` call is intentionally commented out.
      Inspect the PR and merge manually once satisfied.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

# ---------------------------------------------------------------------------
# Bootstrap: add python/ to sys.path so the shared libraries are importable.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO_ROOT / "python"))

import gh  # noqa: E402 — must come after sys.path is patched
import git  # noqa: E402
import proc  # noqa: E402
import pytest_ci_timing  # noqa: E402
from errors import ShipError, TransientNetworkError  # noqa: E402
from harness_ci_timing import (  # noqa: E402
    TimingRow,
    compute_medians,
    median_shard_totals,
    parse_log,
    untimed_targets,
)
from harness_makefile import read_shards, write_shards  # noqa: E402
from harness_shard_packer import pack  # noqa: E402


class _ProcRunner:
    """Adapter wrapping the module-level ``proc.run`` as a ``Runner`` instance."""

    def run(
        self,
        argv: Any,
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Any = None,
        check: bool = False,
        stdout: Any = None,
        stderr: Any = None,
    ) -> proc.CommandResult:
        return proc.run(
            list(argv),
            timeout=timeout,
            cwd=cwd,
            env=env,
            check=check,
            stdout=stdout,
            stderr=stderr,
        )


_RUNNER = _ProcRunner()
_GUARD = "test-harness-shards-coverage"
_ASSIGNMENTS_PATH = _REPO_ROOT / "python" / "shard-assignments.json"


@dataclass(frozen=True)
class HarnessPlan:
    current_shards: dict[int, list[str]]
    new_shards: dict[int, list[str]]
    medians: dict[str, float]
    n_shards: int
    baseline_spread: float


@dataclass(frozen=True)
class PythonPlan:
    assignments: dict[str, int]
    medians: dict[str, float]
    n_shards: int


@dataclass(frozen=True)
class RebalancePlan:
    harness: HarnessPlan | None
    python: PythonPlan | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        msg = f"must be >= 1, got {parsed}"
        raise argparse.ArgumentTypeError(msg)
    return parsed


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebalance test shards based on CI timing."
    )
    parser.add_argument("--repo", help="owner/name (auto-detected if omitted)")
    parser.add_argument("--kind", choices=("harness", "python", "all"), default="all")
    parser.add_argument("--n-runs", type=_positive_int, default=5, help="baseline CI runs to sample")
    parser.add_argument("--branch-prefix", default="rebalance-shards")
    parser.add_argument("--n-verify-runs", type=_positive_int, default=3)
    parser.add_argument("--n-python-shards", type=_positive_int, default=4)
    parser.add_argument("--balance-threshold", type=float, default=15.0)
    parser.add_argument(
        "--max-shard-wall-clock",
        type=float,
        default=60.0,
        help="real per-shard CI job wall-clock budget in seconds (jobs-API verdict)",
    )
    parser.add_argument("--workflow", default="ci.yaml")
    parser.add_argument("--baseline-branch", default="main")
    return parser.parse_args(argv)


def _detect_repo(runner: _ProcRunner) -> str:
    """Return ``owner/name`` for the current git remote (origin)."""
    result = runner.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        cwd=str(_REPO_ROOT),
    )
    if result.returncode != 0:
        print(f"ERROR: could not detect repo name: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def _validate_partition() -> bool:
    """Run the structural partition checker; return True on success."""
    result = subprocess.run(
        ["bash", "scripts/test-harness-shards-coverage.sh"],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print("ERROR: partition validation failed:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


def _git_checkout_branch(branch: str) -> bool:
    """Switch to *branch*; return True on success."""
    result = _RUNNER.run(["git", "checkout", branch], cwd=str(_REPO_ROOT))
    if result.returncode != 0:
        print(
            f"ERROR: 'git checkout {branch}' failed (rc={result.returncode}):\n"
            f"{result.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def _wait_for_completed_run(
    runner: _ProcRunner,
    *,
    repo: str,
    branch: str,
    workflow: str,
    exclude: list[int],
    timeout_s: int = 1800,
    poll_s: int = 30,
) -> int:
    """Poll until a successful completed run appears that is not in *exclude*."""
    exclude_set = set(exclude)
    deadline = time.monotonic() + timeout_s
    start = time.monotonic()

    while True:
        elapsed = int(time.monotonic() - start)
        result = runner.run(
            [
                "gh", "run", "list",
                "--repo", repo,
                "--branch", branch,
                "--workflow", workflow,
                "--limit", "15",
                "--json", "databaseId,status,conclusion",
            ],
            cwd=str(_REPO_ROOT),
        )
        if result.returncode == 0:
            runs = json.loads(result.stdout or "[]")
            for run in runs:
                rid = int(run["databaseId"])
                if rid in exclude_set:
                    continue
                status = run.get("status", "")
                conclusion = run.get("conclusion") or ""
                if status == "completed":
                    if conclusion == "success":
                        return rid
                    msg = (
                        f"Run {rid} completed with conclusion={conclusion!r} "
                        f"on branch {branch!r}"
                    )
                    raise RuntimeError(msg)
            in_progress = [
                r["databaseId"]
                for r in runs
                if int(r["databaseId"]) not in exclude_set and r.get("status") != "completed"
            ]
            if in_progress:
                print(f"    [{elapsed}s] {len(in_progress)} run(s) in progress …", flush=True)
            else:
                print(f"    [{elapsed}s] no runs visible yet …", flush=True)
        else:
            print(f"    [{elapsed}s] gh run list failed (rc={result.returncode}); retrying …", flush=True)

        if time.monotonic() >= deadline:
            break
        time.sleep(poll_s)

    msg = f"No new successful CI run appeared within {timeout_s}s on branch {branch!r}"
    raise TimeoutError(msg)


def _trigger_and_wait(
    runner: _ProcRunner,
    *,
    repo: str,
    branch: str,
    workflow: str,
    exclude: list[int],
    run_label: str,
) -> int:
    """Trigger a workflow_dispatch run and wait for it to complete successfully."""
    print(f"  {run_label}: triggering workflow_dispatch on {branch!r} …")
    dispatch_result = gh.workflow_dispatch(runner, workflow, repo=repo, ref=branch)
    if dispatch_result.returncode != 0:
        msg = (
            f"workflow_dispatch failed (rc={dispatch_result.returncode}): "
            f"{dispatch_result.stderr.strip()}"
        )
        raise RuntimeError(msg)
    time.sleep(20)
    run_id = _wait_for_completed_run(
        runner,
        repo=repo,
        branch=branch,
        workflow=workflow,
        exclude=exclude,
    )
    print(f"    Completed run {run_id} ✓")
    return run_id


def _trigger_verification_runs(
    runner: _ProcRunner,
    *,
    repo: str,
    branch: str,
    workflow: str,
    n_verify_runs: int,
    exclude: Sequence[int] = (),
) -> list[int]:
    """Trigger verification CI runs and return their run ids."""
    verify_run_ids = list(exclude)
    new_run_ids: list[int] = []
    for i in range(n_verify_runs):
        run_id = _trigger_and_wait(
            runner,
            repo=repo,
            branch=branch,
            workflow=workflow,
            exclude=verify_run_ids,
            run_label=f"Run {i + 1}/{n_verify_runs}",
        )
        verify_run_ids.append(run_id)
        new_run_ids.append(run_id)
    return new_run_ids


def _collect_log_rows(runner: _ProcRunner, run_id: int, *, repo: str) -> list[TimingRow]:
    result = gh.run_log_read(runner, run_id, repo=repo)
    if result.returncode != 0:
        print(
            f"  WARNING: could not fetch log for run {run_id} (rc={result.returncode})",
            file=sys.stderr,
        )
        return []
    return parse_log(result.stdout, run_id)


def _collect_pytest_log_rows(
    runner: _ProcRunner, run_id: int, *, repo: str
) -> list[pytest_ci_timing.PytestTimingRow]:
    result = gh.run_log_read(runner, run_id, repo=repo)
    if result.returncode != 0:
        print(
            f"  WARNING: could not fetch log for run {run_id} (rc={result.returncode})",
            file=sys.stderr,
        )
        return []
    return pytest_ci_timing.parse_log(result.stdout, run_id)


def _print_shard_table(
    label: str,
    shards_def: dict[int, list[str]],
    medians: dict[str, float],
) -> None:
    """Print a per-shard total-seconds table derived from target medians."""
    rows = []
    for n in sorted(shards_def):
        total = sum(medians.get(t, 0.0) for t in shards_def[n])
        rows.append((n, total))
    print(f"\n{label}")
    print(f"  {'Shard':>6}  {'Total (s)':>10}")
    for n, total in rows:
        print(f"  {n:>6}  {total:>10.1f}")
    totals = [t for _, t in rows]
    if totals:
        spread = max(totals) - min(totals)
        print(f"  Spread (max-min): {spread:.1f}s")


def _select_packed_workload(
    medians: dict[str, float],
    all_shard_targets: list[str],
) -> dict[str, float]:
    """Return the measured target set that will be passed to ``pack``."""
    shard_target_set = set(all_shard_targets)
    return {t: medians[t] for t in medians if t in shard_target_set}


def _check_feasibility(
    new_shards: dict[int, list[str]],
    medians: dict[str, float],
    balance_threshold: float,
) -> None:
    """Warn when the packed shard spread exceeds the configured threshold."""
    if not new_shards:
        return

    rows = [
        (shard_n, sum(medians.get(target, 0.0) for target in targets))
        for shard_n, targets in new_shards.items()
    ]
    totals = [total for _, total in rows]
    if not totals:
        return

    spread = max(totals) - min(totals)
    if spread <= balance_threshold:
        return

    heaviest_shard, heaviest_total = max(rows, key=lambda row: row[1])
    lightest_shard, lightest_total = min(rows, key=lambda row: row[1])

    print("\nWARNING: packed workload may be infeasible for the configured balance threshold.")
    print(f"  Estimated packed spread: {spread:.1f}s")
    print(f"  Balance threshold: {balance_threshold:.1f}s")
    print(f"  Heaviest shard: {heaviest_shard} ({heaviest_total:.1f}s)")
    print(f"  Lightest shard: {lightest_shard} ({lightest_total:.1f}s)")
    print("  Continuing anyway; rebalancing may still improve spread.")


def _collect_wall_clock(
    runner: _ProcRunner,
    run_ids: list[int],
    *,
    repo: str,
) -> dict[int, float]:
    """Return ``{shard: median real CI wall-clock seconds}`` across *run_ids*."""
    per_shard: dict[int, list[float]] = {}
    for run_id in run_ids:
        try:
            durations = gh.job_durations(runner, run_id, repo=repo)
        except (ShipError, TransientNetworkError) as exc:
            print(
                f"  WARNING: could not fetch real wall-clock for run {run_id}: {exc}",
                file=sys.stderr,
            )
            continue
        for shard, seconds in durations.items():
            per_shard.setdefault(shard, []).append(seconds)
    return {shard: median(values) for shard, values in per_shard.items()}


def _report_wall_clock_balance(
    wall_clock: dict[int, float],
    *,
    max_shard_wall_clock: float,
    n_verify_runs: int,
) -> bool:
    """Print the real per-shard wall-clock table and verdict."""
    slowest_shard, slowest = max(wall_clock.items(), key=lambda item: item[1])
    fastest = min(wall_clock.values())
    spread = slowest - fastest
    over_budget = sorted(shard for shard, secs in wall_clock.items() if secs > max_shard_wall_clock)

    print(f"\nReal CI job wall-clock (jobs API, median of {n_verify_runs} verification runs):")
    print(f"  {'Shard':>6}  {'Wall-clock (s)':>14}")
    for shard_n in sorted(wall_clock):
        marker = "  <-- over budget" if wall_clock[shard_n] > max_shard_wall_clock else ""
        print(f"  {shard_n:>6}  {wall_clock[shard_n]:>14.1f}{marker}")
    print(f"  Slowest shard: {slowest_shard} ({slowest:.1f}s)")
    print(f"  Spread (max-min): {spread:.1f}s")
    print(f"  Budget (--max-shard-wall-clock): {max_shard_wall_clock:.1f}s")

    if over_budget:
        print(
            f"⚠ Shard balance FAILED: {len(over_budget)} shard(s) over the "
            f"{max_shard_wall_clock:.1f}s wall-clock budget: {over_budget}"
        )
        return False
    print(
        f"✓ Shard balance VERIFIED: slowest shard {slowest:.1f}s within "
        f"{max_shard_wall_clock:.1f}s budget"
    )
    return True


def _pack_nodeids(medians: dict[str, float], n_shards: int) -> dict[str, int]:
    """Pack pytest nodeids into ``1..n`` shard ids by LPT."""
    packed = pack(medians=medians, n_shards=n_shards, guard="")
    assignments: dict[str, int] = {}
    for shard_id, nodeids in packed.items():
        for nodeid in nodeids:
            assignments[nodeid] = shard_id
    return assignments


def _assignments_json_text(assignments: dict[str, int]) -> str:
    return json.dumps(assignments, sort_keys=True, indent=2) + "\n"


def _write_assignments_json(path: Path, assignments: dict[str, int]) -> None:
    """Atomically write pytest shard assignments."""
    tmp_path = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    try:
        tmp_path.write_text(_assignments_json_text(assignments), encoding="utf-8")
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def _assert_artifact_paths_clean(paths: list[str]) -> None:
    """Raise when any selected artifact path has local git dirt."""
    dirty: list[str] = []
    for path in paths:
        result = git.status_porcelain_paths(_RUNNER, path, cwd=str(_REPO_ROOT))
        if result.returncode != 0:
            stderr = result.stderr.strip() or f"returncode {result.returncode}"
            raise ShipError(f"git status failed for {path}: {stderr}")
        if result.stdout.strip():
            dirty.append(path)
    if dirty:
        msg = "refusing to rebalance with dirty artifact path(s): " + ", ".join(dirty)
        raise ShipError(msg)


def _revert_written_paths(paths: list[str]) -> None:
    """Restore staged and working-tree state for written artifact paths."""
    for path in paths:
        restore = git.restore_staged(_RUNNER, path, cwd=str(_REPO_ROOT))
        if restore.returncode != 0:
            stderr = restore.stderr.strip() or f"returncode {restore.returncode}"
            raise ShipError(f"git restore --staged failed for {path}: {stderr}")
        checkout = git.checkout_paths(_RUNNER, path, cwd=str(_REPO_ROOT))
        if checkout.returncode != 0:
            stderr = checkout.stderr.strip() or f"returncode {checkout.returncode}"
            raise ShipError(f"git checkout -- failed for {path}: {stderr}")


def _paths_for_kind(kind: str) -> list[str]:
    paths: list[str] = []
    if kind in {"harness", "all"}:
        paths.append("Makefile")
    if kind in {"python", "all"}:
        paths.append("python/shard-assignments.json")
    return paths


def _path_would_match(path: Path, text: str) -> bool:
    return path.exists() and path.read_text(encoding="utf-8") == text


def _paths_to_stage(kind: str, plan: RebalancePlan) -> list[str]:
    paths: list[str] = []
    if kind in {"harness", "all"} and plan.harness is not None:
        paths.append("Makefile")
    if kind in {"python", "all"} and plan.python is not None:
        paths.append("python/shard-assignments.json")
    return paths


def _plan_is_noop(plan: RebalancePlan, makefile_path: Path) -> bool:
    harness_noop = plan.harness is None
    if plan.harness is not None:
        before = read_shards(makefile_path)
        harness_noop = before == plan.harness.new_shards
    python_noop = plan.python is None
    if plan.python is not None:
        python_noop = _path_would_match(
            _ASSIGNMENTS_PATH, _assignments_json_text(plan.python.assignments)
        )
    return harness_noop and python_noop


def _commit_subject(kind: str) -> str:
    labels = {"all": "harness+python", "harness": "harness", "python": "python"}
    return f"chore: rebalance test shards ({labels[kind]})"


def _create_pr_body(args: argparse.Namespace, plan: RebalancePlan) -> str:
    legs: list[str] = []
    files: list[str] = []
    if plan.harness is not None:
        legs.append("harness")
        files.append("Makefile")
    if plan.python is not None:
        legs.append("python")
        files.append("python/shard-assignments.json")
    body = [
        "Automatically generated by `/rebalance-tests`.",
        "",
        f"- Legs: {', '.join(legs)}",
        f"- Files: {', '.join(files)}",
        f"- Baseline: {args.n_runs} successful runs on `{args.baseline_branch}`",
        "- Merge remains operator-owned.",
    ]
    if plan.harness is not None:
        body.append(
            f"- Harness estimated packed spread: {plan.harness.baseline_spread:.1f}s"
        )
    if plan.python is not None:
        body.append(
            f"- Python nodeids assigned: {len(plan.python.assignments)} across {plan.python.n_shards} shards"
        )
    return "\n".join(body) + "\n"


def _prepare_harness_plan(args: argparse.Namespace, repo: str, makefile_path: Path) -> HarnessPlan:
    print("\n[gate:harness] Reading current Makefile shard layout …")
    current_shards = read_shards(makefile_path)
    n_shards = len(current_shards)
    all_shard_targets: list[str] = []
    for targets in current_shards.values():
        all_shard_targets.extend(targets)
    print(f"  {n_shards} shards, {len(all_shard_targets)} total targets")

    print(
        f"\n[gate:harness] Fetching timing from last {args.n_runs} successful CI runs "
        f"on {args.baseline_branch!r} …"
    )
    baseline_runs = gh.run_list_successful(
        _RUNNER,
        repo=repo,
        branch=args.baseline_branch,
        workflow=args.workflow,
        limit=args.n_runs,
    )
    if not baseline_runs:
        raise ShipError("no successful CI runs found on main; cannot compute harness baseline")

    all_timing_rows: list[TimingRow] = []
    for run in baseline_runs:
        print(f"  Fetching log for run {run.database_id} …")
        rows = _collect_log_rows(_RUNNER, run.database_id, repo=repo)
        all_timing_rows.extend(rows)
        print(f"    {len(rows)} timing rows")

    if not all_timing_rows:
        raise ShipError("no LARCH_HARNESS_TIMING rows found in any CI run log")

    medians = compute_medians(all_timing_rows)
    print(f"  Medians computed for {len(medians)} targets")

    untimed = untimed_targets(all_shard_targets=all_shard_targets, medians=medians)
    if untimed:
        print(
            f"\nERROR: refusing to rebalance — {len(untimed)} shard target(s) "
            "have NO timing data:",
            file=sys.stderr,
        )
        for target in sorted(untimed):
            print(f"  - {target}", file=sys.stderr)
        raise ShipError("untimed test-harness target(s) found")

    print(f"\n[gate:harness] Packing {n_shards} shards with round-robin LPT …")
    measured = _select_packed_workload(medians, all_shard_targets)
    new_shards = pack(medians=measured, n_shards=n_shards, guard=_GUARD)
    _check_feasibility(new_shards, medians, args.balance_threshold)
    totals = [sum(medians.get(t, 0.0) for t in ts) for ts in new_shards.values()]
    spread = max(totals) - min(totals) if totals else 0.0
    return HarnessPlan(current_shards, new_shards, medians, n_shards, spread)


def _prepare_python_plan(args: argparse.Namespace, repo: str) -> PythonPlan:
    print(
        f"\n[gate:python] Fetching pytest durations from last {args.n_runs} successful CI runs "
        f"on {args.baseline_branch!r} …"
    )
    rows = pytest_ci_timing.fetch_timing_rows(
        _RUNNER,
        repo=repo,
        branch=args.baseline_branch,
        workflow=args.workflow,
        n_runs=args.n_runs,
    )
    if not rows:
        raise ShipError("no parseable python-tests --durations=0 call rows found")
    observed = pytest_ci_timing.observed_shard_count(rows)
    if observed is None:
        raise ShipError("conflicting or missing python-tests shard X of N totals in CI logs")
    if observed != args.n_python_shards:
        raise ShipError(
            f"--n-python-shards={args.n_python_shards} does not match observed CI shard count {observed}"
        )
    latest_rows = pytest_ci_timing.rows_latest_attempt_per_shard(rows)
    medians = pytest_ci_timing.compute_medians(latest_rows)
    if not medians:
        raise ShipError("no pytest nodeid medians after latest-attempt dedup")
    assignments = _pack_nodeids(medians, args.n_python_shards)
    print(f"  Packed {len(assignments)} nodeids across {args.n_python_shards} shards")
    return PythonPlan(assignments=assignments, medians=medians, n_shards=args.n_python_shards)


def _write_selected_artifacts(plan: RebalancePlan, makefile_path: Path) -> list[str]:
    written: list[str] = []
    if plan.harness is not None:
        print("\n[write:harness] Writing updated shard lines to Makefile …")
        write_shards(makefile_path=makefile_path, shards=plan.harness.new_shards)
        written.append("Makefile")
        print("\n[write:harness] Validating partition with test-harness-shards-coverage.sh …")
        if not _validate_partition():
            print("ERROR: partition invalid — reverting Makefile changes", file=sys.stderr)
            _revert_written_paths(["Makefile"])
            raise ShipError("harness partition validation failed")
        print("  Partition valid ✓")
    if plan.python is not None:
        print("\n[write:python] Writing python/shard-assignments.json …")
        try:
            _write_assignments_json(_ASSIGNMENTS_PATH, plan.python.assignments)
        except Exception as exc:
            print(f"ERROR: writing assignments JSON failed: {exc}", file=sys.stderr)
            if written:
                _revert_written_paths(written)
            raise ShipError("assignments JSON write failed") from exc
        written.append("python/shard-assignments.json")
    return written


def _commit_push_and_pr(
    args: argparse.Namespace,
    *,
    repo: str,
    branch_name: str,
    original_branch: str,
    plan: RebalancePlan,
    paths_to_stage: list[str],
) -> gh.PullRequest:
    print(f"\n[git] Creating branch {branch_name!r} and pushing …")
    res = git.branch(_RUNNER, branch_name, cwd=str(_REPO_ROOT))
    if res.returncode != 0:
        raise ShipError(f"git branch failed: {res.stderr.strip()}")

    if not _git_checkout_branch(branch_name):
        _git_checkout_branch(original_branch)
        raise ShipError("git checkout branch failed")

    res = git.add(_RUNNER, *paths_to_stage, cwd=str(_REPO_ROOT))
    if res.returncode != 0:
        _git_checkout_branch(original_branch)
        raise ShipError(f"git add failed: {res.stderr.strip()}")
    res = git.commit(_RUNNER, _commit_subject(args.kind), cwd=str(_REPO_ROOT))
    if res.returncode != 0:
        _git_checkout_branch(original_branch)
        raise ShipError(f"git commit failed: {res.stderr.strip()}")

    res = git.push_set_upstream(_RUNNER, "origin", branch_name, cwd=str(_REPO_ROOT))
    if res.returncode != 0:
        _git_checkout_branch(original_branch)
        raise ShipError(f"git push failed: {res.stderr.strip()}")

    print(f"  Switching back to {original_branch!r} …")
    _git_checkout_branch(original_branch)

    print("\n[pr] Creating PR …")
    pr, created = gh.pr_create(
        _RUNNER,
        repo=repo,
        branch=branch_name,
        title=_commit_subject(args.kind),
        body=_create_pr_body(args, plan),
        base="main",
        draft=False,
    )
    print(f"  PR #{pr.number}: {pr.url} ({'created' if created else 'existing'})")
    return pr


def _verify_harness(args: argparse.Namespace, verify_run_ids: list[int], *, repo: str, plan: HarnessPlan) -> None:
    print("\n[verify:harness] Collecting timing and verifying shard balance …")
    wall_clock = _collect_wall_clock(_RUNNER, verify_run_ids, repo=repo)
    if wall_clock:
        _ = _report_wall_clock_balance(
            wall_clock,
            max_shard_wall_clock=args.max_shard_wall_clock,
            n_verify_runs=len(verify_run_ids),
        )
    else:
        print(
            "WARNING: no real job wall-clock available from the jobs API; "
            "relying on the LARCH_HARNESS_TIMING sum estimate below.",
            file=sys.stderr,
        )

    verify_rows: list[TimingRow] = []
    for run_id in verify_run_ids:
        print(f"  Fetching log for run {run_id} …")
        verify_rows.extend(_collect_log_rows(_RUNNER, run_id, repo=repo))

    if not verify_rows:
        if not wall_clock:
            print("WARNING: could not collect any timing from verification runs.", file=sys.stderr)
        return

    medians_verify = median_shard_totals(verify_rows)
    max_shard = max(medians_verify.values())
    min_shard = min(medians_verify.values())
    spread = max_shard - min_shard
    threshold = args.balance_threshold

    print(f"\nSum-of-timing estimate spread: {spread:.1f}s (threshold: {threshold}s)")
    if spread <= threshold:
        print("✓ Sum estimate within threshold")
    else:
        print(f"⚠ Sum estimate over threshold (spread {spread:.1f}s > {threshold}s)")

    _print_shard_table("BEFORE (estimated from baseline medians):", plan.new_shards, plan.medians)
    print(f"\nAFTER (measured sum median of {args.n_verify_runs} verification runs):")
    print(f"  {'Shard':>6}  {'Total (s)':>10}")
    for shard_n in sorted(medians_verify):
        print(f"  {shard_n:>6}  {medians_verify[shard_n]:>10.1f}")
    print(f"  Spread (max-min): {spread:.1f}s")


def _verify_python(
    args: argparse.Namespace,
    verify_run_ids: list[int],
    *,
    repo: str,
    pr_url: str,
) -> int:
    print("\n[verify:python] Collecting python-tests timing and verifying shard balance …")
    verify_rows: list[pytest_ci_timing.PytestTimingRow] = []
    for run_id in verify_run_ids:
        print(f"  Fetching log for run {run_id} …")
        verify_rows.extend(_collect_pytest_log_rows(_RUNNER, run_id, repo=repo))

    if not verify_rows:
        print(
            "ERROR: zero parseable python-tests --durations=0 rows in verification runs.",
            file=sys.stderr,
        )
        print(f"  PR is at {pr_url}", file=sys.stderr)
        return 1

    totals = pytest_ci_timing.median_shard_totals(verify_rows)
    expected = set(range(1, args.n_python_shards + 1))
    missing = sorted(expected - set(totals))
    if missing:
        print(f"ERROR: python-tests verification missing shard ids: {missing}", file=sys.stderr)
        print(f"  PR is at {pr_url}", file=sys.stderr)
        return 1

    spread = max(totals.values()) - min(totals.values())
    print(f"\nPython pytest duration spread: {spread:.1f}s (threshold: {args.balance_threshold}s)")
    print(f"  {'Shard':>6}  {'Total (s)':>10}")
    for shard_n in sorted(totals):
        print(f"  {shard_n:>6}  {totals[shard_n]:>10.1f}")
    if spread > args.balance_threshold:
        print(
            f"ERROR: python-tests spread {spread:.1f}s exceeds {args.balance_threshold:.1f}s.",
            file=sys.stderr,
        )
        print(f"  PR is at {pr_url}", file=sys.stderr)
        return 1
    print("✓ Python shard balance within threshold")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:  # noqa: C901
    args = _parse_args(argv)
    makefile_path = _REPO_ROOT / "Makefile"
    repo = args.repo or _detect_repo(_RUNNER)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    branch_name = f"{args.branch_prefix}-{timestamp}"
    original_branch = git.try_current_branch(_RUNNER, cwd=str(_REPO_ROOT)) or "main"

    print(f"Repo   : {repo}")
    print(f"Kind   : {args.kind}")
    print(f"Branch : {branch_name}")

    try:
        harness_plan = None
        python_plan = None
        if args.kind in {"harness", "all"}:
            harness_plan = _prepare_harness_plan(args, repo, makefile_path)
        if args.kind in {"python", "all"}:
            python_plan = _prepare_python_plan(args, repo)
        plan = RebalancePlan(harness=harness_plan, python=python_plan)

        artifact_paths = _paths_for_kind(args.kind)
        _assert_artifact_paths_clean(artifact_paths)
        if _plan_is_noop(plan, makefile_path):
            print("\nNo shard artifact changes needed; exiting before branch creation.")
            return 0

        written_paths = _write_selected_artifacts(plan, makefile_path)
        paths_to_stage = [path for path in _paths_to_stage(args.kind, plan) if path in written_paths]
        if not paths_to_stage:
            print("\nNo shard artifact changes needed after write; exiting before branch creation.")
            return 0

        try:
            pr = _commit_push_and_pr(
                args,
                repo=repo,
                branch_name=branch_name,
                original_branch=original_branch,
                plan=plan,
                paths_to_stage=paths_to_stage,
            )
        except ShipError:
            _git_checkout_branch(original_branch)
            _revert_written_paths(paths_to_stage)
            raise

        print(
            f"\n[verify] Triggering {args.n_verify_runs} verification CI runs via workflow_dispatch …"
        )
        try:
            verify_run_ids = _trigger_verification_runs(
                _RUNNER,
                repo=repo,
                branch=branch_name,
                workflow=args.workflow,
                n_verify_runs=args.n_verify_runs,
            )
        except (TimeoutError, RuntimeError) as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            print(f"  PR is at {pr.url} — investigate CI failure before retrying.", file=sys.stderr)
            return 1

        if plan.harness is not None:
            _verify_harness(args, verify_run_ids, repo=repo, plan=plan.harness)
        if plan.python is not None:
            result = _verify_python(args, verify_run_ids, repo=repo, pr_url=pr.url)
            if result != 0:
                return result

        print(f"\nPR #{pr.number} is ready for review: {pr.url}")
        print("Merge is commented out. Verify the PR and merge manually when satisfied.")
        return 0
    except ShipError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
