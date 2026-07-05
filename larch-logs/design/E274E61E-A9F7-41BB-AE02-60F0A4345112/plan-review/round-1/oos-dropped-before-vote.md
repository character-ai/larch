### OOS_5: Recovered-PR ship tests do not assert the new DONE Outcome bullet
- **Description**: Recovered-PR ship tests do not assert the new DONE Outcome bullet. Scenario: `test_recovered_open_pr_preconciles_stalled_summary_before_merge` and the draft variant only assert `- **Outcome**: stalled` is absent after recovery; they would still pass if the Outcome bullet were missing entirely
- **Reviewer**: Cursor-dyn-Final Report Contract
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: python/tests/implement/test_ship.py:1311-1327
- **Phase**: design

