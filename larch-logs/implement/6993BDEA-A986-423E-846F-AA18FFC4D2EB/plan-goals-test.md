## Goal
Treat "This workflow is already running" from `gh run rerun` as a success rather than a failure in `ci-rerun-failed.sh`, preventing the evaluate_failure path from unnecessarily stalling when CI is already running.

## Implementation Plan

### Files to modify
1. `scripts/ci-rerun-failed.sh` — add `elif` branch to detect "already running" error
2. `scripts/ci-rerun-failed.md` — document new behavior

### Files to create
3. `scripts/test-ci-rerun-failed.sh` — regression harness (stub gh, test 3 cases)
4. `scripts/test-ci-rerun-failed.md` — sibling stub pointing to primary

### Files to update
5. `Makefile` — add test-ci-rerun-failed to .PHONY, test-harnesses-7, and add recipe after test-ci-status

### Approach
In `ci-rerun-failed.sh`: after the `if [[ $RERUN_EXIT -eq 0 ]]` block, add an `elif` that checks if `$RERUN_OUTPUT` contains "already running" (case-insensitive). When matched: set `RERUN_SUBMITTED=true` and `ERROR=""`. This treats the in-progress run as equivalent to a successfully submitted rerun — no retry needed since CI is already running.

### Edge cases
- The "already running" match is case-insensitive to tolerate any capitalization drift in the GitHub CLI's error message.
- The existing `ERROR` default covers any unexpected exit path via the EXIT trap.

### Test plan
Run `make test-ci-rerun-failed` to verify all 3 cases pass.
