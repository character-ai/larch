### OOS_2: No dedicated h3-level fixture in regression pin
- **Description**: No dedicated h3-level fixture in regression pin. Scenario: STRUCTURED_BODY uses only ## headings; a #{2,3} regression in _HEADING_RE would not be caught independently of the new h4 test
- **Reviewer**: Cursor-dyn-Markdown Parser Correctness
- **Severity**: nit
- **Focus area**: correctness
- **Location**: python/tests/issue/test_learn_from_bugs.py:25-43
- **Phase**: design

