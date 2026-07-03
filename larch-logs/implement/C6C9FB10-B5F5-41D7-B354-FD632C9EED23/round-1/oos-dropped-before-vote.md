### OOS_1: [OUT_OF_SCOPE] Stale shard nodeids after the test renames
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-cli-envelope
- **Severity**: nit
- **Concern**: The shard map still lists old `test_design_parse_argv_*` nodeids after the rename to `test_design_parse_flags_*`, so a subset of tests remains misassigned in shard bookkeeping. This is shard-hygiene debt only; round-robin fallback still runs the orphaned tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Refresh `python/shard-assignments.json` via `/rebalance-tests` when convenient.
  - From cursor-specialist-testing: Refresh via /rebalance-tests when convenient.
  - From dyn-dyn-cli-envelope: Refresh assignments with `/rebalance-tests` or update the renamed nodeids in the same change set.

### OOS_2: [OUT_OF_SCOPE] Parser edge-case coverage is still implicit
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The documented parser edge cases (`--difficulty` missing/invalid, no args, and `--` separator) do not have dedicated pytest coverage, so future edits could change those behaviors without a focused regression signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add parametrized accept/reject cases for the documented edge-case list.

