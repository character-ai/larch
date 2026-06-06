### FINDING_1:
- **Reviewer(s)**: Cursor-dyn-pipeline-state-handoff
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-tally-code-votes.sh:63-64
- **Concern**: skills/review/scripts/test-tally-code-votes.sh (plan § test-tally). Scenario: Proposed tests keep OOS_ACCEPTED_COUNT checks on tally stdout only; emit-tally reads --tally-file (production: review-tally.env via TALLY_FILE), where the counter is appended at tally-code-votes.sh:776-783
- **Proposed resolution**: A regression that dropped the review-tally.env append while leaving emit_kv stdout intact would pass test-tally but emit-tally preserve would see a missing key, coerce to 0, and still run serialize/truncate—reproducing #3550 on the review-core path In at least one OOS/scope-drift case, assert awk -F= '$1=="OOS_ACCEPTED_COUNT"{print $2}' "$TMP/review-tally.env" equals the expected count (mirror the existing ACCEPTED_COUNT file assertion at line 62)

### FINDING_2:
- **Reviewer(s)**: Cursor-dyn-oos-consumer-coverage
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:868-909
- **Concern**: New harness skills/shared/scripts/test-normalize-oos-block-header.sh is not registered in any test-harnesses-N shard. Scenario: Shared helper contract regressions will not run under make lint / CI; sibling skills/shared/scripts/test-oos-serialize.sh is wired via test-harnesses-9
- **Proposed resolution**: Add a Makefile test-normalize-oos-block-header target and include it in an existing shard (e.g. test-harnesses-9 beside test-oos-serialize)
