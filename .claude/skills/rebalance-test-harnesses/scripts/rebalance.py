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
_REPO_ROOT = Path(
    subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
)
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


def _wait_for_completed_run(
    runner: _ProcRunner,
    *,
    repo: str,
    branch: str,
    exclude: list[int],
    timeout_s: int = 1800,
    poll_s: int = 30,
) -> int:
    """Poll until a successful completed run appears that is not in *exclude*.

    Returns the ``databaseId`` of the new run, or raises ``TimeoutError``.
    """
    exclude_set = set(exclude)
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        time.sleep(poll_s)
        result = runner.run(
            [
                "gh", "run", "list",
                "--repo", repo,
                "--branch", branch,
                "--limit", "15",
                "--json", "databaseId,status,conclusion",
            ],
            cwd=str(_REPO_ROOT),
        )
        if result.returncode != 0:
            continue
        runs = json.loads(result.stdout or "[]")
        for run in runs:
            rid = int(run["databaseId"])
            if rid in exclude_set:
                continue
            if run.get("status") == "completed" and run.get("conclusion") == "success":
                return rid
    msg = f"No new successful CI run appeared within {timeout_s}s on branch {branch!r}"
    raise TimeoutError(msg)


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

    print(f"Repo : {repo}")
    print(f"Branch: {branch_name}")

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
    baseline_rows = gh.run_list_successful(
        _RUNNER,
        repo=repo,
        branch=args.baseline_branch,
        workflow=args.workflow,
        limit=args.n_runs,
    )
    if not baseline_rows:
        print("ERROR: no successful CI runs found on main. Cannot compute baseline.", file=sys.stderr)
        return 1

    all_timing_rows: list[TimingRow] = []
    for run in baseline_rows:
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
    # Only pack targets that are actually in the current shard layout
    measured = {t: medians[t] for t in medians if t in all_shard_targets}
    new_shards = pack(measured, n_shards, guard=_GUARD, extras=extras)

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
    git.branch(_RUNNER, branch_name, cwd=str(_REPO_ROOT))
    # git.branch doesn't check out; check out manually
    _RUNNER.run(["git", "checkout", branch_name], cwd=str(_REPO_ROOT))
    git.add(_RUNNER, "Makefile", cwd=str(_REPO_ROOT))
    git.commit(
        _RUNNER,
        "chore: rebalance test harness shards via round-robin LPT",
        cwd=str(_REPO_ROOT),
    )
    git.push_set_upstream(_RUNNER, "origin", branch_name, cwd=str(_REPO_ROOT))

    # ------------------------------------------------------------------
    # Step 7: Create PR
    # ------------------------------------------------------------------
    print("\n[7/9] Creating PR …")
    baseline_spread = (
        max(sum(medians.get(t, 0.0) for t in ts) for ts in current_shards.values())
        - min(sum(medians.get(t, 0.0) for t in ts) for ts in current_shards.values())
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
    # Step 8: Wait for 3 CI verification runs
    # ------------------------------------------------------------------
    print(f"\n[8/9] Waiting for {args.n_verify_runs} verification CI runs …")
    verify_run_ids: list[int] = []
    for i in range(args.n_verify_runs):
        if i == 0:
            print(f"  Run {i + 1}/{args.n_verify_runs}: waiting for PR-push-triggered run …")
        else:
            print(f"  Run {i + 1}/{args.n_verify_runs}: triggering via workflow_dispatch …")
            # Small delay so GitHub registers the previous run before we trigger another
            time.sleep(15)
            gh.workflow_dispatch(
                _RUNNER, args.workflow, repo=repo, ref=branch_name
            )
            time.sleep(15)

        try:
            run_id = _wait_for_completed_run(
                _RUNNER,
                repo=repo,
                branch=branch_name,
                exclude=verify_run_ids,
            )
        except TimeoutError as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            return 1

        print(f"    Completed run {run_id} ✓")
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

        # After/before comparison
        _print_shard_table("BEFORE (estimated from baseline medians):", current_shards, medians)
        _print_shard_table("AFTER (median of verification runs):", new_shards, medians_verify)

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
