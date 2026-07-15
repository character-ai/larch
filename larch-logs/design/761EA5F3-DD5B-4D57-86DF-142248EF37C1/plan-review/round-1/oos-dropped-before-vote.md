### OOS_4: Plan overclaims preservation of Cursor unit tests
- **Description**: Plan overclaims preservation of Cursor unit tests. Scenario: Testing strategy says preserve Cursor preflight, wrap-failure, startup-lock, and diagnostic tests, but test_checks.py only has argv-shape coverage; those behaviors are untested at the lane level
- **Reviewer**: Cursor-dyn-Descriptor Lane Integration
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/tests/implement/test_checks.py:2814-2887
- **Phase**: design

