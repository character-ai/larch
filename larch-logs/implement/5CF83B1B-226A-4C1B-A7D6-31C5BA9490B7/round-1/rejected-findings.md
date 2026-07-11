### [rejected] FINDING_10

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_10: Delegate assessment-kind validation to normalize_kinds
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `parse_requested_kinds` duplicates a hard-coded `invariants|guidelines` allowlist instead of relying on Piece 2 `normalize_kinds`. A future Python-only assessment kind could be rejected through a divergent Bash path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Remove the Bash allowlist and delegate unknown-kind handling to normalize_kinds in compute_launch_identity.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (0 YES)

### FINDING_11: Register the new assessment harness in Makefile and CI
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: `test-step-8-assessment.sh` is not included in the Makefile test-harness targets or CI shards. Adapter regressions in identity rejoin, retry, and fail-closed behavior can therefore merge without a default-branch harness run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add test-step-8-assessment Makefile target mirror test-step-8-ship and register it on a test-harnesses shard
  - From codex-specialist-testing: Add a dedicated test target and include it in the appropriate test-harnesses shard.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (0 YES)

### FINDING_13: Revalidate fail-closed publication paths and values
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: Fail-closed publication does not consistently revalidate the result path, temporary path, or values immediately before replacement. A symlink swap, malformed `BGJOB_RC`, or unsafe temporary path could redirect writes or corrupt the line-oriented result envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Use the common validated atomic writer and recheck temporary and destination paths before replacement.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
