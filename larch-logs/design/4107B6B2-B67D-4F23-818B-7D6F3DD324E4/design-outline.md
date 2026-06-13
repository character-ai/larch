## Proposed Design Outline

### Goals
- Detect merge-conflict race (conflict signal in `admin_failed` error) before reclassifying as `review_required`.
- Return `MAIN_ADVANCED` when a conflict is detected at merge time, triggering the existing CI monitor rebase loop.
- Add a regression test for the new detection path.

### Non-goals
- Fix the bash legacy path (`ship-pr.sh` / `merge-pr.sh`).
- Introduce a new `MERGE_RESULT_CONFLICT_RACE` constant.
- Check or enforce the rebase budget inside `_maybe_review_required`.

### Approach sketch
- Add a module-private tuple `_MERGE_CONFLICT_SIGNALS` in `merge.py` with the three keywords from the bug report.
- In `_maybe_review_required`, after confirming `review_decision == "REVIEW_REQUIRED"`, check `outcome.error` against that tuple.
- If any signal matches, return `MergeResult(result=MERGE_RESULT_MAIN_ADVANCED, error=outcome.error)` instead of `MERGE_RESULT_REVIEW_REQUIRED`.
- Add one test in `test_merge.py`: admin + plain merge fail with conflict keywords, `review_decision` returns `REVIEW_REQUIRED`, result is `MAIN_ADVANCED`.
- Update existing `test_merge_pr_review_required_after_admin_failed` (non-conflict keywords) confirms still returns `REVIEW_REQUIRED`.

### Surfaces in scope
- `python/merge.py`
- `python/test_merge.py`

### Open questions
- None.
