### OOS_1:
- **Description**: Three new `monitor()` outcome tests are unrelated to ship resume/counter restore. Scenario: The SIMPLE plan’s core fix is `run_ship()` resume + terminal counter threading; `test_ship.py` already stubs `ci_monitor.monitor` for handback/cap cases. Adding monitor bail/transient/local-unfixable coverage expands scope (~60+ lines) without exercising new resume code.
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/test_ci_monitor.py:80-84
- **Phase**: design

### OOS_2:
- **Description**: Monitor-level outcome tests unrelated to resume/counter hardening. Scenario: Extra ~30–60 LOC and maintenance surface without protecting the stated acceptance criteria
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/test_ci_monitor.py:planned-additions
- **Phase**: design

