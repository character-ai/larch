### [rejected] FINDING_1

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_1: Regression coverage misses real helper statuses and comment URLs
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: The stall-recovery regression does not exercise the real helper comment URL or Tier A no-match / lookup-failed-open statuses, so a normalization wiring bug could still pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Parametrize helper stdout fixtures for no-match unknown and empty status asserting STALL_RECOVERY_REPORT_* output and no raw FILE_FAILURE_REPORT_* keys.
  - From codex-specialist-testing: Add parametrized cases for the actual dedup comment URL plus no-match and lookup-failed-open, and assert issue aliases appear only for issue URLs.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

