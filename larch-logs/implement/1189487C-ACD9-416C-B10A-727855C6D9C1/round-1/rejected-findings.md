### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: step-6-entry lacks wrapper-level bgjob regression coverage
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: The new Step 6 bgjob wrapper is not exercised end-to-end in a regression test. Existing Python tests stop at `step6_entry_main`, so wrapper-level bugs in `bgjob start`, merge-env truncation, or launcher stdout could still escape CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: step 7a lacks a real bgjob-cycle integration test
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: The Step 7a bgjob path is only covered by stubbed argv-shape and isolated result-env tests. Nothing runs the real `--bgjob-launch true` cycle far enough to prove child merge-result writing, `WAIT`/`DONE` handling, and continuation gating on `BGJOB_RC=0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0

