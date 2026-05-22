## Goal
Add branch guards to ship-pr.sh and step2-implement.sh to prevent commits landing on main when feature branch creation fails

## Implementation Plan
## Plan

## Files to modify

1. **`scripts/ship-pr.sh`** — Add branch guard at start of `run_bump_phase()`.
2. **`scripts/ship-pr.md`** — Document `bump-branch-guard` stall step and guard behavior.
3. **`skills/implement/scripts/step2-implement.sh`** — Add `main-branch-prohibited` bail after SPAWN_BRANCH capture.
4. **`skills/implement/scripts/step2-implement.md`** — Add `main-branch-prohibited` to bail-reason table.
5. **`skills/implement/SKILL.md`** — Section 2.2 `STATUS=complete` path: add post-dispatch branch assertion.
6. **`scripts/test-ship-pr.sh`** — Update `write_state`/`make_repo` for non-protected branch; add two guard tests.
7. **`skills/implement/scripts/test-step2-dispatch.sh`** — Add test for `main-branch-prohibited` bail.

### Guard 1 — `ship-pr.sh` `run_bump_phase()`

Insert after the `local` declaration (line 808), before `emit_breadcrumb`:

```bash
local _bump_guard_branch _bump_guard_state_branch _bump_guard_fail
_bump_guard_state_branch=$(read_state BRANCH_NAME)
_bump_guard_branch=$(git branch --show-current 2>/dev/null || echo "")
if [[ "$_bump_guard_state_branch" == "main" || "$_bump_guard_state_branch" == "master" \
    || "$_bump_guard_branch" != "$_bump_guard_state_branch" ]]; then
    _bump_guard_fail=$(failure_capture_path bump)
    printf 'bump-branch-guard: BRANCH_NAME=%s current=%s\n' \
        "$_bump_guard_state_branch" "$_bump_guard_branch" > "$_bump_guard_fail"
    record_failure bump "bump-branch-guard" 1 "$_bump_guard_fail"
    exit_stall bump-branch-guard
fi
```

Stalls with `STALL_STEP=bump-branch-guard` and exit code 4 before any bump work. Catches both the "committed on main" incident and branch-mismatch scenarios.

### Guard 2 — `step2-implement.sh` spawn-branch check

Insert after `SPAWN_BRANCH=$(cat "$SPAWN_BRANCH_FILE")` (line 297):

```bash
# Bail if spawned on a protected branch — feature branch creation must have failed.
if [[ "$SPAWN_BRANCH" == "main" || "$SPAWN_BRANCH" == "master" ]]; then
    emit_bailed "main-branch-prohibited"
fi
```

Uses the existing `emit_bailed` pattern (exits 0, STATUS=bailed). Fires before any external implementer is launched, on both first and resume invocations.

### Guard 3 — SKILL.md orchestrator post-Step-2 assertion

In section 2.2, the `STATUS=complete` bullet is extended: after the Phantom Untracked Probe, run `git-current-branch.sh` and assert `CURRENT_BRANCH_POST_DISPATCH == BRANCH_NAME`. On mismatch, print a warning, log to `execution-issues.md`, set `STALL_TRACKING=true`, and bail to Step 12d with `REASON=main-branch-post-dispatch`.


## Test plan

**`scripts/test-ship-pr.sh`**:
- `write_state`: change `BRANCH_NAME=master` → `BRANCH_NAME=feature/test-issue-7`
- `make_repo`: add `git -C "$root" checkout -q -b feature/test-issue-7` after initial commit
- Add Test A: `BRANCH_NAME=main` in state → exit 4, `STALL_STEP=bump-branch-guard`
- Add Test B: `BRANCH_NAME=feature/wrong-branch` in state → exit 4, `STALL_STEP=bump-branch-guard`

**`skills/implement/scripts/test-step2-dispatch.sh`**:
- Add Test Nm: cursor invocation with git repo on `main` branch → `STATUS=bailed REASON=main-branch-prohibited TOOL=cursor`
