### OOS_1: Add MAIN_HEALTH_MAX_TRANSIENT_RETRIES duplicates existing CI_MONITOR_TRANSIENT_RERUN_MAX=1
- **Description**: Add MAIN_HEALTH_MAX_TRANSIENT_RETRIES duplicates existing CI_MONITOR_TRANSIENT_RERUN_MAX=1. Scenario: A second constant with the same bound can drift from CI_MONITOR_TRANSIENT_RERUN_MAX without behavioral benefit for this narrow fix.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/core/config.py:687
- **Phase**: design



