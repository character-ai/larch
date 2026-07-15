### OOS_2: [OUT_OF_SCOPE] Update the stale "Production launchers must not import this module yet" banner once `checks_lint_fix` imports `_vendor`.
- **Description**: [OUT_OF_SCOPE] Update the stale "Production launchers must not import this module yet" banner once `checks_lint_fix` imports `_vendor`.. Scenario: The module docstring will contradict production usage after this piece lands; it does not affect runtime behavior.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/agents/_vendor.py:1-7
- **Phase**: design

