### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: owner-death starts bgjob before identity is ready
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The owner-death scenario launches `start_bgjob` immediately after backgrounding the owner, without waiting for identity capture to become ready. On slow CI, `start_bgjob` can fail to capture the owner PID’s identity before orphan handling is tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: orphan monitor tests can ignore monkeypatched grace timing
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The orphan monitor tests monkeypatch `BGJOB_OWNER_GRACE_S` but not the `LARCH_TEST_BGJOB_*` environment overrides, so exported `LARCH_TEST_BGJOB_OWNER_GRACE_S` values can bypass the monkeypatch and validate the wrong timing path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

