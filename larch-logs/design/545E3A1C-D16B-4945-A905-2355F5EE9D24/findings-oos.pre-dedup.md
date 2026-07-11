### OOS_1: Local fence helper duplicates G-Md-3 reuse guidance instead of sharing issue_create._balanced_fence_line_indices
- **Description**: Local fence helper duplicates G-Md-3 reuse guidance instead of sharing issue_create._balanced_fence_line_indices. Scenario: Drift between parsers could diverge on marker length or suffix rules over time
- **Reviewer**: Cursor-dyn-Markdown Parser Correctness
- **Severity**: minor
- **Focus area**: architecture
- **Location**: ARCHITECTURAL_GUIDELINES.md:303-306
- **Phase**: design



### OOS_2: No dedicated h3-level fixture in regression pin
- **Description**: No dedicated h3-level fixture in regression pin. Scenario: STRUCTURED_BODY uses only ## headings; a #{2,3} regression in _HEADING_RE would not be caught independently of the new h4 test
- **Reviewer**: Cursor-dyn-Markdown Parser Correctness
- **Severity**: nit
- **Focus area**: correctness
- **Location**: python/tests/issue/test_learn_from_bugs.py:25-43
- **Phase**: design



