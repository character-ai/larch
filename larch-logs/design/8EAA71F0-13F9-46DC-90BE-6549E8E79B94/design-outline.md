## Proposed Design Outline

### Goals
- Stop `review-and-fix commit-fixes --stage-all` exiting 1 when every collected review-delta path is already committed clean.
- Treat an all-clean collected set as a benign noop, extending the #5715 empty-list guard to the nonempty-but-all-clean case.
- Still commit the dirty subset correctly when the collected set is partially clean.

### Non-goals
- No baseline-ownership logic. Regenerated ratchet baselines (`*-baseline.json`) are not staged or reverted here. That is a separate ownership question.
- No change to `_collect_review_fix_stage_paths` collection semantics.
- No change to `_stage_and_commit_round` in coder_runner.py (sibling commits fresh-edited in-round paths; all-clean is not reachable there).

### Approach sketch
- In `_commit_fixes_stage_all`, after collecting paths, intersect them with the actually-dirty paths from `git status --porcelain`.
- Empty intersection emits the existing noop contract (`COMMITTED=false`, `COMMIT_OUTCOME=noop`) and returns 0.
- Non-empty intersection writes only the dirty subset to the stage file before the existing `git commit --only --pathspec-from-file` call.
- Reuse the `_run` runner and existing KV helpers. No new subprocess pattern.
- G-Fix-1 deviation: list the sibling `_stage_and_commit_round` (coder_runner.py:330) in the PR body as intentionally different.

### Surfaces in scope
- `python/larch/review/review_and_fix.py` (`_commit_fixes_stage_all`).

### Open questions
- None.
