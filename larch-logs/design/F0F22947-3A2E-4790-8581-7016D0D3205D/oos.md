### OOS_1: Share env KV validation with `design_wire` instead of copying `_KEY_RE` / unsafe-value checks
- **Description**: Share env KV validation with `design_wire` instead of copying `_KEY_RE` / unsafe-value checks. Scenario: `session.py` and the proposed `write_result_env` would duplicate the same validation rules, which may drift later.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/support/session.py:55-112
- **Phase**: design

Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

