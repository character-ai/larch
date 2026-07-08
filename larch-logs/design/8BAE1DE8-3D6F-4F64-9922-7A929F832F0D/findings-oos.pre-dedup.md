### OOS_1: Retry breadcrumb still says fresh panel during targeted revote
- **Description**: Retry breadcrumb still says fresh panel during targeted revote. Scenario: The degraded-entry breadcrumb is hard-coded to “retrying with fresh panel,” which will misreport logs when only voters rerun.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/review/round_runner.py:490
- **Phase**: design



### OOS_2: Degraded retry breadcrumb still says fresh panel during targeted revote
- **Description**: Degraded retry breadcrumb still says fresh panel during targeted revote. Scenario: The degraded entry breadcrumb always prints "retrying with fresh panel" before choosing targeted vs full retry, which misstates the cheaper under-quorum path called out in prior OOS ledger rows.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/review/round_runner.py:490
- **Phase**: design



