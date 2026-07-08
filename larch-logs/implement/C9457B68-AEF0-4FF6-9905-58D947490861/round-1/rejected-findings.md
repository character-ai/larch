### [rejected] FINDING_7

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_7: Resume CI still lacks a parent-launcher case
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: Resume CI only exercises `--bgjob-child` cases, so the new parent-launcher contract for `step-5-resume.sh` is untested and regressions can ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Add a non-child resume case that asserts the exact launcher stdout and `bgjob start` argv.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

