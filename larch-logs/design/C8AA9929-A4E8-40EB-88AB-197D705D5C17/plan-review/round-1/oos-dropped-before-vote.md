### OOS_4: Persist resolved base remote/ref at Step 0
- **Description**: Persist resolved base remote/ref at Step 0. Scenario: Repeated symbolic-ref resolution at pre-commit and ship-time could diverge if remote HEAD moves mid-run
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/state/bootstrap.py:1963
- **Phase**: design

