## Goal
Fix spurious DROPPED=false from drop-bump-commit.sh when untracked larch-log files are in the repo worktree, ensuring reliable drop-and-rebump cycles.

## Implementation Plan
1. Change Guard 1 in `scripts/drop-bump-commit.sh` to use `git status --porcelain --untracked-files=no` so untracked files don't block the drop (`git reset --hard` doesn't affect them).
2. Remove step-7 post-push flush from `run_rebase_rebump()` in `scripts/ship-pr.sh` (always a no-op, but risks a flush commit on top of bump if ever active).
3. Update `scripts/drop-bump-commit.md` and `scripts/ship-pr.md`.
4. Add untracked-file test to `scripts/test-drop-bump-commit.sh`.

## Test plan
- Run test-drop-bump-commit.sh and verify new untracked-file case passes.
- Run /relevant-checks after implementation.
