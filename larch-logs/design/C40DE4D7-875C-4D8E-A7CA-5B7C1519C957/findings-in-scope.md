### FINDING_1: Recycled-PID reap scenario exercises the wrong branch
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The scenario for `bgjob reap` can still make both liveness checks fail, so `reap_main` fast-unlinks the row instead of exercising the expired terminate path that proves the recycled PID is not signaled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep the row expired but leave daemon liveness live, or otherwise arrange for only one liveness check to fail before `reap_main` reaches termination.
  - From Cursor-Innovation: Revise scenario 5: either use an expired row where daemon_liveness stays true via a live decoy identity while child fields point at a recycled PID with corrupted identity, or drop the harness terminate-branch requirement and prove no-signal on the both-dead fast-unlink path while leaving terminate coverage to test_reap.py case 2
  - From Codex-Innovation: Keep the daemon alive for scenario 5, force expiry, and use the live recycled child mismatch to drive `reap_main` through the terminate branch before unlinking.
  - From Codex-Pragmatic: Make scenario 5 keep daemon_liveness live=True with a harness-owned placeholder daemon identity, force expiry and no result env, and corrupt only the recorded CHILD_* identity for the live recycled PID so reap reaches the expired terminate branch and proves the PID is not signaled.
  - From Cursor-Requirements: `reap_main` checks `result or (not child_live.live and not daemon_live.live)` before `entry_expired` (`python/larch/bgjob/cli.py:122-126`). With daemon dead and a live recycled PID whose recorded child identity mismatches, both `child_liveness` and `daemon_liveness` are false (`python/larch/bgjob/registry.py:162-173`). Reap unlinks at 122-124 and never calls `terminate_validated_process_group`, so the harness can pass while failing to prove the no-signal terminate path the plan and issue require
  - From Codex-Requirements: Change scenario 5 to keep a live identity-valid daemon record, keep the row expired, and make only the recorded child identity mismatch the live recycled PID. Then assert reap unlinks the row and the recycled PID remains live after terminate_validated_process_group rejects the recorded child identity.

### FINDING_2: Teardown traps can kill the recycled owner without rechecking identity
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The cleanup traps can still tear down the recycled PID by raw PID/PGID after the scenario has passed, without revalidating that the process is still the same owner.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Track the recorded identity for each started process and check it again in teardown, or exclude the recycled-owner PID from trap cleanup.

### FINDING_3: Owner-death wait budget may be too short
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The owner-death scenario needs three consecutive owner-validation failures before the grace timer starts, so a wait budget that only covers grace plus one poll can still flake on slower runners.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin an explicit wait budget in scenario 2: at least three poll intervals at the overridden poll rate, plus the overridden grace window, plus small slack; fail with diagnostics if BGJOB_RC=orphaned is not observed in time

### FINDING_4: Invalid timing overrides should fail before `STARTED`
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: The new test-only override helpers only read env inside the monitor loop, so a malformed override can surface after the job has already been registered and `STARTED` has been printed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add a preflight parse before the child registers or prints STARTED, while keeping the call-time reads in `_check_owner_validation` and `_monitor`.

### FINDING_5: Budget-expiry test does not prove the child group was killed
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The budget-expiry scenario only checks for `BGJOB_RC=timeout`, so it can pass even if the daemon reports timeout but leaves the long-running child or process group alive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Capture the child pid or recorded identity from the registry before waiting, then after BGJOB_RC=timeout assert the recorded child or process group is no longer live before cleanup runs
