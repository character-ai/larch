### OOS_1: [OUT_OF_SCOPE] No regression test for shard-total dedupe behavior
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `shard_totals_per_run` deduplicates duplicate `(run_id, shard, target)` rows but has no unit test covering that behavior. A revert or partial refactor could restore incorrect summation of retry-duplicate timing rows; existing tests use unique targets per shard so CI would not catch doubled or wrong shard totals in rebalance verification. Pre-existing gap, amplified by this commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test_shard_totals_per_run_dedupes_duplicate_targets (or extend test_shard_totals_per_run_basic) with two rows for the same target and assert last-wins summation; optionally cover median_shard_totals on that input.


