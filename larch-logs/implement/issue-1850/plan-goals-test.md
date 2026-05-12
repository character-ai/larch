## Goal
Pin the post-`/bump-version` anti-halt directives in both `skills/implement/SKILL.md` (Step 8 direct path) and `skills/implement/references/rebase-rebump-subprocedure.md` with regression-test assertions in `scripts/test-implement-anti-halt.sh`.

## Implementation Plan

### Files to modify
1. `scripts/test-implement-anti-halt.sh` — add two `check_contains` assertions
2. `scripts/test-implement-anti-halt.md` — update description to mention new checks and issue #1850

### Approach
Add two new `check_contains` calls in the existing `/implement step-boundary anti-halt coverage` section:
- Pin `"before that Bash call is a halt in disguise that skips sub-steps 3/3b"` in `skills/implement/SKILL.md`
- Pin `"in the tool result is NOT a run-completion signal"` in `skills/implement/references/rebase-rebump-subprocedure.md`

## Test plan
Run `bash scripts/test-implement-anti-halt.sh` — all existing assertions plus the two new ones should pass.
