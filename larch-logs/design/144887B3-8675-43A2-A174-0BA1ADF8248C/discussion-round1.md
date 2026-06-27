## Decision 1: Fix approach
- **Question**: What outcome for the escalation-success report — refactor to reduce complexity, or accept the baseline bump?
- **Resolution**: Refactor `step2b_drafter_main` so all four complexity metrics return to their pre-#5630 values (C901 ≤28, PLR0911 ≤11, PLR0912 ≤30, PLR0915 ≤123), then revert the four `python/complexity-baseline.json` entries to those pre-fold numbers. Undoes the ratchet introduced by PR #5630.
- **Source**: user

## Decision 2: Behavior preservation (hard constraint)
- **Question**: May the refactor change `step2b_drafter_main`'s runtime behavior?
- **Resolution**: No. Pure extraction only. The `DRAFTER_NEXT_ACTION` dispatch values, exit codes, printed `DRAFTER_VENDOR=`/contract rows, sentinel/file writes, and pause + postplan semantics must stay identical. Existing tests (`test_design_lifecycle.py`, the design-step2b/structure harnesses) must pass unchanged.
- **Source**: codebase

## Decision 3: Scope boundary (non-goal)
- **Question**: Should other over-baseline functions in `design_lifecycle.py` be refactored too?
- **Resolution**: No. Scope is limited to `step2b_drafter_main` and its four baseline entries. Sibling offenders (`route_main`, `failure_report_core`, `step0_route_main`, `driver_main`, etc.) are out of scope. New extracted helpers should themselves stay under complexity thresholds so no new baseline entries are needed (or only minimal ones).
- **Source**: codebase
