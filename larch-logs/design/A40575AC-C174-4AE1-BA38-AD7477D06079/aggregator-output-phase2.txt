These are two distinct findings (different files and fixes). Verifying the cited locations so the normalized concerns stay accurate.
Two independent gaps: tally tests assert `OOS_ACCEPTED_COUNT` on stdout only while production reads `review-tally.env`, and a new OOS normalize harness is not wired into `make lint` shards. No merge between them.

### FINDING_1: OOS_ACCEPTED_COUNT not asserted on review-tally.env in test-tally
- **Reviewer(s)**: Cursor-dyn-pipeline-state-handoff
- **Severity**: important
- **Concern**: `skills/review/scripts/test-tally-code-votes.sh` (plan § test-tally) asserts `OOS_ACCEPTED_COUNT` only against tally stdout (`$out` at lines 63–64). Production `emit-tally` reads `--tally-file` (`review-tally.env` via `TALLY_FILE`); `tally-code-votes.sh` appends `OOS_ACCEPTED_COUNT` to that file at lines 776–783. A regression that dropped the `review-tally.env` append while leaving `emit_kv` stdout intact would pass test-tally but cause emit-tally preserve to see a missing key, coerce to 0, and still run serialize/truncate—reproducing #3550 on the review-core path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-pipeline-state-handoff: A regression that dropped the review-tally.env append while leaving emit_kv stdout intact would pass test-tally but emit-tally preserve would see a missing key, coerce to 0, and still run serialize/truncate—reproducing #3550 on the review-core path In at least one OOS/scope-drift case, assert awk -F= '$1=="OOS_ACCEPTED_COUNT"{print $2}' "$TMP/review-tally.env" equals the expected count (mirror the existing ACCEPTED_COUNT file assertion at line 62)

### FINDING_2: test-normalize-oos-block-header.sh not registered in Makefile harness shard
- **Reviewer(s)**: Cursor-dyn-oos-consumer-coverage
- **Severity**: important
- **Concern**: New harness `skills/shared/scripts/test-normalize-oos-block-header.sh` is not registered in any `test-harnesses-N` shard. Shared helper contract regressions will not run under `make lint` / CI. Sibling `skills/shared/scripts/test-oos-serialize.sh` is wired via `test-harnesses-9` (Makefile lines 91 and 907–908).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-oos-consumer-coverage: Add a Makefile test-normalize-oos-block-header target and include it in an existing shard (e.g. test-harnesses-9 beside test-oos-serialize)
