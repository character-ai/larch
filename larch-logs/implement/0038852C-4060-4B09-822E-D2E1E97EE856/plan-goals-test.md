## Goal
Implement issue #4045: [IMPLEMENTING] [BUG] (URGENT) rebase.py: PrePushConflictHandoff not triggered when fixer waterfall reports partial success, leaving main agent unable to intervene\n\n## Summary.

## Implementation Plan
## Summary

`python/rebase.py::_resolve_conflicts` raises `Stalled("conflicts remain after fixer waterfall")` when a fixer tier returns a winning result but unmerged paths remain. The `PrePushConflictHandoff` escape hatch — which would let the main agent intervene — is only checked when **all** fixer tiers fail (`waterfall.winning_tier is None`). A partially-successful fixer that leaves residual conflicts bypasses the handoff entirely and stalls the run with no main-agent recovery path.

## Observed in

- Run `F6CA1F7C-AC36-4F2F-B89E-1994A2814AB5`, PR #4031
- `ship.py: rebase: Flush+Push` step during CI-monitor loop
- Conflicts in: `Makefile`, `SECURITY.md`, `python/cli.py`, `python/migrated-scripts.tsv`

## Symptoms

1. `step-8-ship.sh` exits with code **4** (`STALLED`).
2. JSON stdout: `{"outcome": "STALLED", "detail": "conflicts remain after fixer waterfall", ...}`
3. Working tree left with `UU` (unresolved) files from an active in-progress rebase.
4. `CALLER_KIND=` is **empty** — `PrePushConflictHandoff` was never raised, so the `ship_pr_pre_push` conflict-resolution path in the orchestrator was never triggered.
5. `stall-recovery-report.sh` classifies the stall as `unrecoverable`, skipping the `step8-shippr` re-entry path.
6. Main agent receives no conflict context and cannot apply fixes.

## Root Cause

### Part 1: Incorrect guard in `_resolve_conflicts`

In `python/rebase.py`, after the fixer waterfall runs:

```python
waterfall = agents.run_waterfall(
    config.FIXER_TIER_ORDER,
    _tier_launch,
    runner=runner,
    cwd=cwd,
)
if waterfall.winning_tier is None:
    # Only here is PrePushConflictHandoff considered:
    if enable_pre_push_handoff and _conflicts_are_non_bump_only(conflict_files):
        _write_handoff_flag(tmpdir)
        raise PrePushConflictHandoff(...)
    raise Stalled("fixer waterfall could not resolve conflicts")
if _unmerged_paths(runner, cwd=cwd):
    # BUG: winning_tier is not None but conflicts remain.
    # PrePushConflictHandoff is NOT considered here.
    raise Stalled("conflicts remain after fixer waterfall")
```

The `enable_pre_push_handoff` + `_conflicts_are_non_bump_only` guard exists only in the all-tiers-failed branch. When a fixer tier applies partial fixes (so `winning_tier is not None`) but leaves residual conflicts, the function falls through to a bare `Stalled` — the handoff path is never evaluated.

**Why this happens in practice:** The Codex/Cursor fixer resolves conflict markers in some files but not all (e.g. resolves 2 of 4 conflicted files). The waterfall sees at least one "successful" tier commit and marks `winning_tier`. The post-fixer `_unmerged_paths` check catches the remaining conflicts, but at that point the handoff branch is unreachable.

### Part 2: Why the main agent was not bailed to

The `PrePushConflictHandoff` exception is the only mechanism by which `rebase.py` signals the orchestrator to take over. When it is not raised:

1. `rebase_and_push` propagates `Stalled` directly to `ship.py`'s main loop.
2. `ship.py` writes a terminal state with `STALL_TRACKING=true` and returns `Outcome.STALLED` (exit 4).
3. `CALLER_KIND` remains empty (never set to `ship_pr_pre_push`), so the orchestrator's Exit 4 routing does not enter the `conflict-resolution.md` Phase 1–4 procedure.
4. Step 18a stall recovery classifies the stall as `unrecoverable` (no readable `BAIL_FAILURE_DETAIL_LOG`, no CI-fix exhaustion class), blocking the `step8-shippr` retry path.
5. The main agent reaches teardown with the rebase still in progress and no actionable conflict context.

## Suggested Fix

In `_resolve_conflicts`, after the fixer waterfall succeeds (`winning_tier is not None`) but `_unmerged_paths` is still non-empty, apply the same `PrePushConflictHandoff` logic that exists for the all-failed branch:

```python
if _unmerged_paths(runner, cwd=cwd):
    remaining = tuple(_unmerged_paths(runner, cwd=cwd))
    if enable_pre_push_handoff and _conflicts_are_non_bump_only(remaining):
        _write_handoff_flag(tmpdir)
        raise PrePushConflictHandoff(
            conflict_files=remaining,
            resume_phase=config.SHIP_PR_RRR_RESUME_PHASE,
            caller_kind=config.SHIP_PR_PRE_PUSH_CALLER_KIND,
        )
    raise Stalled(_redact_outbound("conflicts remain after fixer waterfall"))
```

This ensures that when a fixer applies partial fixes but leaves residual conflicts, the orchestrator's main-agent conflict-resolution path (Exit 4 + `CALLER_KIND=ship_pr_pre_push` + `conflict-resolution.md`) is invoked instead of silently stalling.

## Additional Observation

During this run the rebase hit conflicts in `python/cli.py` (the central dispatch registry) and `Makefile` (shard assignments and `.PHONY` targets) — both files that have high contention across concurrent PRs in this repo. These are exactly the kinds of structural conflicts that automated fixers handle poorly. The handoff to the main agent is the correct resolution strategy for these files; the current code prevents it from firing.

## Workaround

Manually abort the rebase (`git rebase --abort`), resolve conflicts by hand, then re-invoke `step-8-ship.sh`.


## Test plan
(no test plan section in plan-file)
