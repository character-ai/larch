## Decision 1: Bounded retry count for the widened empty-output condition
- **Question**: The issue offers two options for the retry count once the empty/missing-output trigger is added: 1 retry (matching #5677 design-voter, minimal structural change) or 4 retries with a 10s delay (matching the code-flow diagram lane from #5732, for cross-lane consistency).
- **Resolution**: Use 1 retry, no delay. Keep the existing if-block shape in `_run_cycle`; only widen the trigger condition to also cover missing/empty output. No new retry-loop or delay constants introduced into this file.
- **Source**: recommended default (no user response within 60s; per terse-answer convention, proceeding with the recommended, smaller-change option)
