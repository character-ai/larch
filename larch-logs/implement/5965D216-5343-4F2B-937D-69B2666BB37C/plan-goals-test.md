## Goal
Implement issue #7073: [IMPLEMENTING] [BUG] review-and-fix commit-fixes --stage-all exits 1 when review-delta paths are clean and only regenerated baselines are dirty.

## Implementation Plan
## Plan

### UPDATED: python/larch/review/review_and_fix.py

- In `_commit_fixes_stage_all`, intersect `_collect_review_fix_stage_paths` results with dirty paths from `git status --porcelain --untracked-files=all`.
- Preserve collected-path order. Write only the dirty subset to `review-fix-stage-paths.txt`.
- Return the existing benign noop contract when the intersection is empty: exit 0, `COMMITTED=false`, and `COMMIT_OUTCOME=noop`.
- Keep the existing commit path and error handling when at least one collected path is dirty.
- Leave `_collect_review_fix_stage_paths`, the non-`--stage-all` path, and baseline-file ownership unchanged.
- Do not change `_stage_and_commit_round`. It commits fresh in-round edits, so the all-clean condition is intentionally unreachable there.

### UPDATED: python/tests/review/test_review_and_fix.py

- Add temporary Git-fixture coverage for a nonempty, fully clean collected set returning the existing noop KVs without invoking a commit.
- Add coverage for a partially dirty collected set committing only dirty collected paths while unrelated dirty baseline files remain unstaged and unmodified.
- Add coverage for an untracked collected file beneath an untracked directory, confirming `--untracked-files=all` includes it in the committed subset.
- Retain assertions for the existing empty-list noop and successful-commit KV contracts.

## Edge cases

- A nonempty but fully clean collected set must not invoke `git commit`.
- A partially clean set must commit only its dirty members.
- Untracked collected files within an otherwise untracked directory must be detected as dirty.
- Unrelated dirty files, including regenerated `*-baseline.json` files, must remain unstaged and unmodified.
- Preserve failure behavior when the status probe or commit command fails.

## Testing strategy

- Run `make test-review-and-fix-commit-fixes`.
- Confirm fixture commit history, stdout KVs, staging state, and worktree state for clean, partially dirty, untracked, and unrelated-baseline cases.

## Acceptance

- Run `make test-review-and-fix-commit-fixes`.
- Confirm fixture commit history, stdout KVs, staging state, and worktree state for clean, partially dirty, untracked, and unrelated-baseline cases.

diff_lines: 34

## Test plan
(no test plan section in plan-file)
