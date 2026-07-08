### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Step 4 offline harness is missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: There is no offline harness for the migrated Step 4 tail wrapper, so stdout, merge, and sentinel regressions can reach production without a dedicated shell test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add test-design-step3b-tail.sh modeled on test-design-step5c.sh and add it to a harness shard.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Step 5c harness coverage and CI wiring are incomplete
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: minor
- **Concern**: The Step 5c harness is not fully integrated into CI and still misses live-row/dead-row registry branches, so rejoin-versus-relaunch regressions can slip by unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add test-design-step5c to a test-harnesses-* target in the Makefile.
  - From codex-specialist-testing: Add live-row and dead-row cases that assert the wrapper emits BGJOB_STATUS=WAIT or BGJOB_STATUS=DEAD and does not relaunch.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

