### OOS_1: [OUT_OF_SCOPE] Stale shard assignments still reference deleted nodeids
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Shard assignments still reference deleted progress-report nodeids, which is CI shard-balancing hygiene rather than a functional coverage gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Refresh `python/shard-assignments.json` via `/rebalance-tests` or remove the orphan rows and pin the migrated nodeid.

