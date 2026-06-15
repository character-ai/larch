### OOS_1:
- **Description**: [SCOPE-REDUCTION] CLI routing-only test duplicates finalize coverage. Scenario: The proposed `cli.main(["session", "kill-background-processes", ...])` dispatcher test only checks registry wiring. `test_finalize.py` already exercises validation and kill behavior for the same entrypoint.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: python/test_cli.py:118-118
- **Phase**: design

