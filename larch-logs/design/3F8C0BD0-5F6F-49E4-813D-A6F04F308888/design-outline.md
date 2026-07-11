## Proposed Design Outline

### Goals
- Fix `teardown()` so it completes even when the coverage artifact is stale after a ci-fix commit.
- Fix `_plan_coverage_summary_line` so `final-report write` completes even when live coverage diverged.

### Non-goals
- Recomputing or refreshing the coverage artifact post-merge.
- Changing the `load_live_coverage` signature or adding a `skip_live_check` flag.
- Fixing any other callers of `load_live_coverage` (`pr_body.py`, pre-merge paths).

### Approach sketch
- In `finalize.py` `teardown()`: wrap the `disposition_link_kind(...)` call in `try/except ShipError`, fall back to `"closes"` and emit a breadcrumb warning.
- In `final_report.py` `_plan_coverage_summary_line`: wrap the `load_live_coverage(...)` call in `try/except ShipError`, return `""` (omit the coverage line from the report).
- Add targeted unit tests in `test_finalize.py` and `test_final_report.py` for both fallback paths.

### Surfaces in scope
- `python/larch/state/finalize.py`
- `python/larch/report/final_report.py`
- `python/tests/state/test_finalize.py`
- `python/tests/report/test_final_report.py`

### Open questions
- None.
