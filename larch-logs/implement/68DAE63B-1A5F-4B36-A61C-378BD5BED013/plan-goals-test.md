## Goal
Add refresh-run-logs.sh to refresh larch-log artifacts before each push in ship-pr.sh

## Implementation Plan
## Implementation Plan

### Goal
Add `scripts/refresh-run-logs.sh` helper that re-renders and commits token/timing larch-log artifacts before each push in ship-pr.sh, with fail-closed post-merge protection.

### Files to create
- `scripts/refresh-run-logs.sh` — helper script (~55 lines)
- `scripts/refresh-run-logs.md` — sibling contract doc
- `scripts/test-refresh-run-logs.sh` — behavioral test harness

### Files to modify
- `scripts/ship-pr.sh` — (a) write MERGE_RESULT to state on merge; (b) Trigger A in run_rebase_rebump before force-push; (c) Trigger B in run_ci_fix_vendor before git-push.sh; (d) Trigger C in run_bump_phase before postbump
- `scripts/ship-pr.md` — document MERGE_RESULT state key and new helper calls
- `skills/implement/SKILL.md` — update --no-logs-commit description and batch table

### Approach
1. `refresh-run-logs.sh`: parse --state-file / --implement-tmpdir; fail-closed if state file missing; skip if MERGE_RESULT=merged|admin_merged; load session-env; re-render token-report + timing-report; write via larch-log.sh; git add + git commit (no push).
2. `ship-pr.sh MERGE_RESULT write`: in run_ci_phase merged|admin_merged case, add state_set MERGE_RESULT. Also in already_merged action.
3. Trigger A (run_rebase_rebump): call helper after step 5 bump and before step 6 force-push.
4. Trigger B (run_ci_fix_vendor): call helper after git-commit and before git-push.sh.
5. Trigger C (run_bump_phase): call helper after bump block, before write_postbump_state.
6. Test harness: 3 test cases (happy path, post-merge skip, probe-failure fail-closed).

### Safety
- Helper exits 0 with no commit on MERGE_RESULT=merged|admin_merged.
- Helper exits 0 with no commit when state file is missing (fail-closed).
- All helper calls in ship-pr.sh use `|| true` so failure is non-fatal.
- No call from implement-finalize.sh teardown or any post-merge path.

## Test plan
(no test plan section in plan-file)
