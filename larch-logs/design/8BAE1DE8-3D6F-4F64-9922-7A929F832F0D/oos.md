### OOS_1: Retry breadcrumb still says fresh panel during targeted revote
- **Description**: Retry breadcrumb still says fresh panel during targeted revote. Scenario: The degraded-entry breadcrumb is hard-coded to “retrying with fresh panel,” which will misreport logs when only voters rerun.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/review/round_runner.py:490
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

