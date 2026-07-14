### OOS_1: [OUT_OF_SCOPE] Module-level `# pylint: disable=all` still bypasses duplicate-code enforcement
- **Description**: [OUT_OF_SCOPE] Module-level `# pylint: disable=all` still bypasses duplicate-code enforcement. Scenario: The new gate targets skip-file and explicit R0801 / duplicate-code disables only. Three runtime modules (`report/tokens.py`, `report/timing.py`, `report/report_tokens_cost.py`) already use module-level `disable=all`, which suppresses R0801 for pylint duplicate-code the same way a blanket disable would.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/report/tokens.py:2
- **Phase**: design



