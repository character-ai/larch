### OOS_1: [OUT_OF_SCOPE] orphan shard assignment for deleted test
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `python/shard-assignments.json:716` still references deleted `test_revise_plan_with_waterfall_records_failed_no_patch`. Dead JSON row after CLI and tests were removed; minor rebalance hygiene drift. Remove the orphan row or refresh `shard-assignments.json`.

