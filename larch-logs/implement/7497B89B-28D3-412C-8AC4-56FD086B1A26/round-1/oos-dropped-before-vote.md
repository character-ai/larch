### FINDING_6: [OUT_OF_SCOPE] Unpinned shard rows
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The new `step0_session` tests lack explicit shard rows, so they fall back to round-robin placement instead of pinned shard assignment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Refresh shard-assignments via /rebalance-tests when convenient

