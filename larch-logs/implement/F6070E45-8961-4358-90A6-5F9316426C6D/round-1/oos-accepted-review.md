### OOS_1: [OUT_OF_SCOPE] Broader implement test coverage gaps per plan
- **Reviewer(s)**: dyn-dyn-oos-priority
- **Severity**: important
- **Concern**: The plan calls for implement tests covering mixed-batch label failure, cap-rollup priority labeling, filtered cleanup, and idempotent backfill on mixed reruns; only provision-failure partial persistence and filed-url backfill are covered today. The duplicate-label-failure path has no test (`test_duplicate_of_url_is_recorded` uses a non-high-risk block).
- **Suggested revisions (informational for voters; coder decides)**:

**Slot coverage**: All eight inventory slots appear in at least one block above (`dyn-dyn-oos-priority` in FINDING_1–3 and OOS_1).
