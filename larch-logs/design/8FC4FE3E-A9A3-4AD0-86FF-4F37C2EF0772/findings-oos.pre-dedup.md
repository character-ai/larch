### OOS_1: Static shell substring tests do not exercise transient owner-probe recovery
- **Description**: Static shell substring tests do not exercise transient owner-probe recovery. Scenario: #6591 is a ~120s owner-grace failure; grep-only launcher tests never model sub-threshold validation blips followed by recovery under fake monotonic time
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/bgjob/test_daemon.py
- **Phase**: design



