### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: `test-bgjob` is not wired into shard coverage
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: `test-bgjob` is missing from shard coverage and the planned shell/integration harness, so CI does not exercise the new bgjob process-group and reap behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Add scripts/test-bgjob.sh or equivalent integration coverage per plan
  - From codex-specialist-testing: Add the shell harness or equivalent subprocess-level cases and wire them into a shard that make lint runs.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

