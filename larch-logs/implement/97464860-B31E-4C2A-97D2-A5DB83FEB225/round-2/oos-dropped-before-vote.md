### OOS_1: [OUT_OF_SCOPE] Mixed-case checkpoint test gap
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The mixed security-sidecar test stubs disposition-checkpoint to success, so it cannot detect the production halt-oos regression or assert NEXT_ACTION=oos-pipeline for the mixed case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add an integration test that uses real disposition_checkpoint_main or asserts NEXT_ACTION=oos-pipeline for the mixed case.

### OOS_2: [OUT_OF_SCOPE] Ballot parse errors fail open
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: _ballot_block_count swallows read/parse errors as zero blocks, so corrupt or unreadable ballots can be treated as empty and skip voting instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Fail closed on OSError/ValueError or propagate tally duplicate-heading errors instead of returning 0.
  - From cursor-specialist-testing: Fail closed or surface parse errors instead of returning zero.

### OOS_3: [OUT_OF_SCOPE] Design OOS one-YES acceptance lacks assertion
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Design two-judge OOS acceptance at one YES is not asserted on oos-accepted-design.md, so accept_oos regressions could ship with only implement-side coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Assert split OOS_1 YES/NO accepts into oos-accepted-design.md while in-scope split stays neutral.

### OOS_4: [OUT_OF_SCOPE] Retired shard assignment still references removed test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Retired pre-vote gate test nodeid remains in shard assignments after test removal, so shard coverage drifts until rebalance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Rebalance shard assignments after retiring pre-vote gate tests.

