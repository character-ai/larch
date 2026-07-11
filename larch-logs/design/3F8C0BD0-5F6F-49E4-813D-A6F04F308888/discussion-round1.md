## Decision 1: Scope of fix — both callers need a guard
- **Question**: Should `final-report write` (step-16-17) also be guarded against `ShipError` from `load_live_coverage`?
- **Resolution**: Yes. `_plan_coverage_summary_line` in `python/larch/report/final_report.py` (line 539) calls `scope_disposition.load_live_coverage` directly. After a ci-fix commit changes the live coverage fingerprint, this call will also raise `ShipError`, propagating uncaught out of `write_final_report_main`. Both callers need a try/except guard.
- **Source**: codebase

## Decision 2: Fallback behavior on ShipError
- **Question**: What should each caller fall back to on ShipError?
- **Resolution**: `teardown()` falls back to `"closes"` link kind (presentational decision, no correctness impact post-merge). `_plan_coverage_summary_line` returns `""` (omits the coverage summary line from the report, graceful degradation).
- **Source**: codebase

## Decision 3: disposition_deferred_inventory is out of scope
- **Question**: Does `disposition_deferred_inventory` (also calling `load_live_coverage`) need the same guard?
- **Resolution**: `disposition_deferred_inventory` is called from `pr_body.py` for PR body creation (pre-merge), not from teardown or final-report. Out of scope for this bug fix.
- **Source**: codebase
