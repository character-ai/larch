### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: orphan monitor tests must clear env overrides before monkeypatching grace
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The orphan-monitor tests monkeypatch grace values, but the test-only env override is read first. If `LARCH_TEST_BGJOB_OWNER_GRACE_S` is exported, the tests become environment-dependent and can stop exercising orphan handling as intended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Delenv both ENV_TEST_BGJOB_* vars in orphan monitor tests or set the env override explicitly to 0 before calling _monitor.
  - From cursor-specialist-testing: Delenv LARCH_TEST_BGJOB_* in tests that patch BGJOB_OWNER_GRACE_S or poll interval


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: budget-expiry should re-check the recorded child identity
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-bgjob-process
- **Severity**: major
- **Concern**: The timeout path only checks `kill -0` on the recorded child PID after `BGJOB_RC=timeout`. That can false-pass if the child died for some other reason, so the test does not prove that timeout enforcement actually killed the recorded process group.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-bgjob-process: Before waiting, capture `CHILD_PID`, `CHILD_START_EPOCH`, and `CHILD_COMM` (or equivalent) from the registry row; after `BGJOB_RC=timeout`, assert `process_identity.validate_process_identity` fails for those recorded fields (or that `registry.child_liveness(entry).live is False`) rather than relying on `kill -0` alone.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: owner-death harness should wait for identity capture before launch
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: The owner-death scenario can race by reusing a fresh PID before process identity capture is ready. On slow CI runners, that can make `bgjob start` fail intermittently before the orphan-death path is exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Wait for `process_identity.read_process_identity(pid=$owner_pid)` to succeed before calling bgjob start.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (0 YES)

### FINDING_10: owner-death should prove the child group is terminated
- **Reviewer(s)**: dyn-dyn-bgjob-process
- **Severity**: major
- **Concern**: Waiting for `BGJOB_RC=orphaned` alone does not prove that `_terminate_child_group` actually ran. A regression that writes `orphaned` without killing the child process group would still pass the current test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-process: After `wait_done_rc ... orphaned`, read `CHILD_PID` (or `CHILD_PGID`) from the registry or capture it before the wait, then assert the child is no longer live via `kill -0` failure or a `process_identity.validate_process_identity` mismatch, mirroring the budget-expiry test’s post-condition.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

