## Proposed Design Outline

### Goals
- OOS_1: stop `_collect_round_stage_paths` from sweeping the whole tree when it has no valid baseline.
- OOS_2: make `_lint_fix_delta_paths` commit only paths a lint-fix iteration reported, excluding non-lint drift.
- OOS_3: close the test gap with a single-path / single-attempt `_verify_post_cleanup_state` regression (test-first).

### Non-goals
- No proactive rewrite of cleanup control flow unless the OOS_3 regression exposes a real bug.
- No change to the `_finalize_failed_cleanup` missing-snapshot whole-tree restore.
- No launcher argv, `STEP5_*` / `LOOP_STATUS`, or lint-fix commit-message-grammar changes.

### Approach sketch
- OOS_1: model `_collect_round_stage_paths` on the safe `_collect_self_review_stage_paths`. Return scoped or empty paths when the snapshot is `missing` or `diff_base` is empty, instead of `_capture_round_tracked_paths()` / `_capture_round_untracked_paths()`.
- OOS_2: treat `unioned_delta_paths` as authoritative, filter it against current state and the pre-lint snapshot, and drop the unconditional `git diff --name-only pre_lint_head` re-scan.
- OOS_3: add a regression through `apply_findings_with_coder` exercising one-path verification failure; add a code fix only if it fails.
- Ship fail-before / pass-after coverage for each code change.

### Surfaces in scope
- `python/review_and_fix.py` — `_collect_round_stage_paths`, `_lint_fix_delta_paths`; cleanup control flow only if the OOS_3 regression demands it.
- `python/test_review_and_fix.py` — new OOS_1, OOS_2, OOS_3 regressions.

### Open questions
- None.
