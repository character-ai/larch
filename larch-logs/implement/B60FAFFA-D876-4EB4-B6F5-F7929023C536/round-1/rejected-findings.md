### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Abandoned bgjob recovery can misclassify live rows and relaunch duplicates
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The stall-recovery path around abandoned-check classification appears to conflate registry visibility, `RESULT_ENV` presence, and daemon/owner liveness. That can miss dead checks, leave stale registry rows behind, or start a second checks daemon while the first is still running.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Mirror step-8-ship.sh: live-registry rejoin, dead-row reap with validated daemon termination before fresh start, and invoke cleanup on the retry path before relaunch.
  - From codex-specialist-edge-cases: Parse the registry row even when RESULT_ENV is absent, then treat missing result env as in-flight only after owner and daemon identities validate; keep result-env existence as the completion check, not the stall-recovery read gate


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Dead cleared registry can regress to abandoned without a no-stall test
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: There is no regression proving that a registry row cleared by `clear_stall_main` still classifies as no-stall on the next `classify_main` run, so a cleared registry could be reinterpreted as abandoned later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: Dead registry rows with result.env lack a no-stall regression
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: There is no regression covering a dead registry row that already has `result.env`, so classify could still mark a finished bgjob abandoned and spuriously emit the retry route.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Legacy Step 5 slug needs dead-registry classify coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The legacy Step 5 slug path is not exercised by a dead-registry classify test, so transitional rows using `implement-step5-self-review` could stop matching silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: clear_stall needs live-row preservation coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `clear_stall` does not have a test proving that a live owner/daemon row without `result.env` survives cleanup, so an abandonment bug could unlink an active registry entry during recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

