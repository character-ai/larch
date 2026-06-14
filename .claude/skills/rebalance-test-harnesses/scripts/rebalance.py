#!/usr/bin/env python3
"""Rebalance CI test harness shards and verify the result.

Run from the repository root::

    python3 .claude/skills/rebalance-test-harnesses/scripts/rebalance.py [flags]

See .claude/skills/rebalance-test-harnesses/SKILL.md for full documentation.

NOTE: the final ``pr_merge`` call is intentionally commented out.
      Inspect the PR and merge manually once satisfied.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Bootstrap: add python/ to sys.path so the shared libraries are importable.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO_ROOT / "python"))

import gh  # noqa: E402 — must come after sys.path is patched
import git  # noqa: E402
from harness_ci_timing import (  # noqa: E402
    TimingRow,
    compute_medians,
    median_shard_totals,
    parse_log,
)
from harness_makefile import read_shards, write_shards  # noqa: E402
from harness_shard_packer import pack  # noqa: E402
import proc  # noqa: E402


# ---------------------------------------------------------------------------
# Minimal Runner adapter that delegates to proc.run
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    """Poll until a successful completed run appears that is not in *exclude*.

    Bug fixes vs original:
    - Check immediately on entry (don't sleep first).
    - Exit early and raise if a non-success run is found (avoids 30-min timeout on CI failure).
    - Print progress on each poll so the operator sees what's happening.
    - Pass --workflow to gh run list to avoid picking up unrelated workflow runs.

    Returns the ``databaseId`` of the new run, or raises ``TimeoutError`` /
    ``RuntimeError`` (on CI failure).
    """
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
                    # CI finished but did not succeed — fail fast
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
    # Give GitHub a moment to register the new run
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


def _collect_log_rows(runner: _ProcRunner, run_id: int, *, repo: str) -> list[TimingRow]:
    result = gh.run_log_read(runner, run_id, repo=repo)
    if result.returncode != 0:
        print(
            f"  WARNING: could not fetch log for run {run_id} (rc={result.returncode})",
            file=sys.stderr,
        )
        return []
    return parse_log(result.stdout, run_id)


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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:  # noqa: C901
    parser = argparse.ArgumentParser(
        description="Rebalance test harness shards based on CI timing."
    )
    parser.add_argument("--repo", help="owner/name (auto-detected if omitted)")
    parser.add_argument("--n-runs", type=int, default=5, help="baseline CI runs to sample")
    parser.add_argument("--branch-prefix", default="rebalance-shards")
    parser.add_argument("--n-verify-runs", type=int, default=3)
    parser.add_argument("--balance-threshold", type=float, default=15.0)
    parser.add_argument("--workflow", default="ci.yaml")
    parser.add_argument("--baseline-branch", default="main")
    args = parser.parse_args(argv)

    makefile_path = _REPO_ROOT / "Makefile"
    repo = args.repo or _detect_repo(_RUNNER)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    branch_name = f"{args.branch_prefix}-{timestamp}"

    # Remember starting branch so we can restore it at the end
    original_branch = git.try_current_branch(_RUNNER, cwd=str(_REPO_ROOT)) or "main"

    print(f"Repo   : {repo}")
    print(f"Branch : {branch_name}")

    # ------------------------------------------------------------------
    # Step 1: Read current shard layout
    # ------------------------------------------------------------------
    print("\n[1/9] Reading current Makefile shard layout …")
    current_shards = read_shards(makefile_path)
    n_shards = len(current_shards)
    all_shard_targets: list[str] = []
    for targets in current_shards.values():
        all_shard_targets.extend(targets)
    print(f"  {n_shards} shards, {len(all_shard_targets)} total targets")

    # ------------------------------------------------------------------
    # Step 2: Fetch baseline timing
    # ------------------------------------------------------------------
    print(
        f"\n[2/9] Fetching timing from last {args.n_runs} successful CI runs "
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
        print("ERROR: no successful CI runs found on main. Cannot compute baseline.", file=sys.stderr)
        return 1

    all_timing_rows: list[TimingRow] = []
    for run in baseline_runs:
        print(f"  Fetching log for run {run.database_id} …")
        rows = _collect_log_rows(_RUNNER, run.database_id, repo=repo)
        all_timing_rows.extend(rows)
        print(f"    {len(rows)} timing rows")

    if not all_timing_rows:
        print("ERROR: no LARCH_HARNESS_TIMING rows found in any CI run log.", file=sys.stderr)
        return 1

    medians = compute_medians(all_timing_rows)
    print(f"  Medians computed for {len(medians)} targets")

    # Targets present in the Makefile shards but absent from timing data
    extras = [
        t for t in all_shard_targets
        if t not in medians and t != _GUARD
    ]
    if extras:
        print(f"  {len(extras)} targets have no timing data (new tests?) → placed at tail")

    # ------------------------------------------------------------------
    # Step 3: Pack shards with round-robin LPT
    # ------------------------------------------------------------------
    print(f"\n[3/9] Packing {n_shards} shards with round-robin LPT …")
    measured = _select_packed_workload(medians, all_shard_targets)
    new_shards = pack(measured, n_shards, guard=_GUARD, extras=extras)
    _check_feasibility(new_shards, medians, args.balance_threshold)

    # ------------------------------------------------------------------
    # Step 4: Write Makefile
    # ------------------------------------------------------------------
    print("\n[4/9] Writing updated shard lines to Makefile …")
    write_shards(makefile_path, new_shards)

    # ------------------------------------------------------------------
    # Step 5: Validate partition
    # ------------------------------------------------------------------
    print("\n[5/9] Validating partition with test-harness-shards-coverage.sh …")
    if not _validate_partition():
        print("ERROR: partition invalid — reverting Makefile changes", file=sys.stderr)
        git.checkout_paths(_RUNNER, "Makefile", cwd=str(_REPO_ROOT))
        return 1
    print("  Partition valid ✓")

    # ------------------------------------------------------------------
    # Step 6: Commit and push
    # ------------------------------------------------------------------
    print(f"\n[6/9] Creating branch {branch_name!r} and pushing …")
    res = git.branch(_RUNNER, branch_name, cwd=str(_REPO_ROOT))
    if res.returncode != 0:
        print(f"ERROR: git branch failed: {res.stderr.strip()}", file=sys.stderr)
        git.checkout_paths(_RUNNER, "Makefile", cwd=str(_REPO_ROOT))
        return 1

    if not _git_checkout_branch(branch_name):
        git.checkout_paths(_RUNNER, "Makefile", cwd=str(_REPO_ROOT))
        _git_checkout_branch(original_branch)
        return 1

    git.add(_RUNNER, "Makefile", cwd=str(_REPO_ROOT))
    res = git.commit(
        _RUNNER,
        "chore: rebalance test harness shards via round-robin LPT",
        cwd=str(_REPO_ROOT),
    )
    if res.returncode != 0:
        print(f"ERROR: git commit failed: {res.stderr.strip()}", file=sys.stderr)
        _git_checkout_branch(original_branch)
        return 1

    res = git.push_set_upstream(_RUNNER, "origin", branch_name, cwd=str(_REPO_ROOT))
    if res.returncode != 0:
        print(f"ERROR: git push failed: {res.stderr.strip()}", file=sys.stderr)
        _git_checkout_branch(original_branch)
        return 1

    # Switch back to the original branch — CI work is done via gh CLI, not git
    print(f"  Switching back to {original_branch!r} …")
    _git_checkout_branch(original_branch)

    # ------------------------------------------------------------------
    # Step 7: Create PR
    # ------------------------------------------------------------------
    print("\n[7/9] Creating PR …")
    baseline_spread = (
        max(sum(medians.get(t, 0.0) for t in ts) for ts in new_shards.values())
        - min(sum(medians.get(t, 0.0) for t in ts) for ts in new_shards.values())
    )
    pr_body = (
        "Automatically generated by `/rebalance-test-harnesses`.\n\n"
        f"- Baseline: {args.n_runs} successful runs on `{args.baseline_branch}`\n"
        f"- Algorithm: round-robin LPT (slowest-first, {n_shards} shards)\n"
        f"- Before spread (estimated): {baseline_spread:.1f}s\n"
        f"- {len(extras)} target(s) with no timing data placed at tail\n\n"
        "After merging, the new shard layout will take effect on the next CI run.\n"
    )
    pr, created = gh.pr_create(
        _RUNNER,
        repo=repo,
        branch=branch_name,
        title="chore: rebalance test harness shards",
        body=pr_body,
        base="main",
        draft=False,
    )
    print(f"  PR #{pr.number}: {pr.url} ({'created' if created else 'existing'})")

    # ------------------------------------------------------------------
    # Step 8: Trigger and wait for N verification CI runs
    # Note: we always use workflow_dispatch — do NOT rely on the pull_request
    # event auto-triggering CI, which is unreliable in some org configurations.
    # ------------------------------------------------------------------
    print(f"\n[8/9] Triggering {args.n_verify_runs} verification CI runs via workflow_dispatch …")
    verify_run_ids: list[int] = []
    for i in range(args.n_verify_runs):
        try:
            run_id = _trigger_and_wait(
                _RUNNER,
                repo=repo,
                branch=branch_name,
                workflow=args.workflow,
                exclude=verify_run_ids,
                run_label=f"Run {i + 1}/{args.n_verify_runs}",
            )
        except (TimeoutError, RuntimeError) as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            print(f"  PR is at {pr.url} — investigate CI failure before retrying.", file=sys.stderr)
            return 1
        verify_run_ids.append(run_id)

    # ------------------------------------------------------------------
    # Step 9: Collect timing and verify balance
    # ------------------------------------------------------------------
    print("\n[9/9] Collecting timing and verifying shard balance …")
    verify_rows: list[TimingRow] = []
    for run_id in verify_run_ids:
        print(f"  Fetching log for run {run_id} …")
        verify_rows.extend(_collect_log_rows(_RUNNER, run_id, repo=repo))

    if not verify_rows:
        print("WARNING: could not collect any timing from verification runs.", file=sys.stderr)
    else:
        medians_verify = median_shard_totals(verify_rows)
        max_shard = max(medians_verify.values())
        min_shard = min(medians_verify.values())
        spread = max_shard - min_shard
        threshold = args.balance_threshold

        print(f"\nVerification spread: {spread:.1f}s (threshold: {threshold}s)")
        if spread <= threshold:
            print("✓ Shard balance VERIFIED")
        else:
            print(f"⚠ Shard balance FAILED (spread {spread:.1f}s > {threshold}s threshold)")

        # BEFORE: per-shard totals estimated from per-target baseline medians
        _print_shard_table("BEFORE (estimated from baseline medians):", new_shards, medians)
        # AFTER: per-shard totals measured directly from verification runs.
        # medians_verify is {shard_int: total_float} — print it directly instead
        # of routing through _print_shard_table (which expects {target: seconds}).
        print(f"\nAFTER (measured median of {args.n_verify_runs} verification runs):")
        print(f"  {'Shard':>6}  {'Total (s)':>10}")
        for shard_n in sorted(medians_verify):
            print(f"  {shard_n:>6}  {medians_verify[shard_n]:>10.1f}")
        print(f"  Spread (max-min): {spread:.1f}s")

    # ------------------------------------------------------------------
    # Merge (COMMENTED OUT — operator must merge manually)
    # ------------------------------------------------------------------
    print(f"\nPR #{pr.number} is ready for review: {pr.url}")
    print("Merge is commented out. Verify the PR and merge manually when satisfied.")
    # Uncomment the following lines to enable auto-merge with --admin:
    # result = gh.pr_merge(_RUNNER, pr.number, repo=repo, admin=True)
    # if result.returncode == 0:
    #     print(f"  PR #{pr.number} merged with --admin ✓")
    # else:
    #     print(f"  ERROR merging PR: {result.stderr.strip()}", file=sys.stderr)
    #     return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
