### OOS_1:
- **Description**: Target retirement contract omits auxiliary .PHONY blocks. Scenario: Retiring test-design-reentry-guard requires removing it from the mega .PHONY on Makefile line 7 and the dedicated .PHONY on line 15. The plan only says remove from .PHONY generically; missing the line-15 cleanup leaves stale Makefile surface but does not break partition guard or shard coverage.
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: Makefile:15,plan.txt:62-72
- **Phase**: design

