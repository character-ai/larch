### [Plan Review] FINDING_2

### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_step5b.py:68-74; python/tests/design/test_design_oos.py:231-290
- **Concern**: [SCOPE-REDUCTION] Plan edits _STEP5B_SKIP_BREADCRUMBS and breadcrumb test literals outside binding acceptance. Scenario: Binding acceptance limits Surface 2 to operator-visible warning strings at 168-269 only; skip breadcrumbs at 68-73 and their exact-pin tests are extra churn and the `oos filing —` grep expands scope beyond the issue title/fix bullets
- **Proposed resolution**: Limit python/larch/design/design_step5b.py edits to the four warning prints at 168, 187, 240, and 269; drop _STEP5B_SKIP_BREADCRUMBS changes, the MAY_UPDATE test block, and the `oos filing —` grep line from validation


