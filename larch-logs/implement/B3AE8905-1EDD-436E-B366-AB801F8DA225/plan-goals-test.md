## Goal
Fix _larch_log_diff_only check to evaluate against pre-fetch origin/main SHA so squash-merged PRs don't block the orphan-drop reset

## Implementation Plan

### Problem

`scripts/local-cleanup.sh` Step 3's `_larch_log_diff_only` check runs
`git diff --name-only origin/main HEAD` AFTER `git fetch origin main` (Step 2).
After a squash-merge, `origin/main` now includes the PR's code files, causing
`_larch_log_diff_only=false` even though all ahead commits are pure larch-log
flushes — so the `git reset --hard origin/main` orphan-drop never fires.

### Fix

**File: scripts/local-cleanup.sh**

1. Capture the pre-fetch SHA immediately before the `git fetch origin main` call
   in Step 2:
   ```
   _pre_fetch_sha=$(git rev-parse origin/main 2>/dev/null || true)
   ```

2. In Step 3's `_larch_log_diff_only` loop, change the diff reference from
   `origin/main` to `${_pre_fetch_sha:-origin/main}` so the diff is evaluated
   against the pre-fetch tip when the SHA was captured, falling back to
   `origin/main` when not.

   Line to change:
   ```
   done < <(git diff --name-only origin/main HEAD 2>/dev/null || true)
   ```
   becomes:
   ```
   done < <(git diff --name-only "${_pre_fetch_sha:-origin/main}" HEAD 2>/dev/null || true)
   ```

**File: scripts/local-cleanup.md**

Update the contract paragraph describing the orphan-drop logic to mention that
the diff is evaluated against the pre-fetch `origin/main` SHA so a
just-landed squash-merge cannot contaminate the `_larch_log_diff_only` check
with the PR's code files.

### Edge cases

- If `git rev-parse origin/main` fails (no remote tracking ref yet), `_pre_fetch_sha`
  is empty and the fallback `${_pre_fetch_sha:-origin/main}` uses `origin/main`,
  preserving pre-fix behavior — correct since no squash-merge has occurred.
- If fetch fails (Step 2 warns but continues), `origin/main` is unchanged from
  `_pre_fetch_sha`, so both forms are equivalent.

### Testing / verification

Run `/relevant-checks` (pre-commit on modified files + agent-lint on full repo).

## Test plan
(no test plan section in plan-file)
