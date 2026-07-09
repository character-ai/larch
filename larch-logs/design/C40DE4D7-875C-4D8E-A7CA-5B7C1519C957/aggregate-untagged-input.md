### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-bgjob.sh
- **Concern**: The recycled-PID reap scenario still sets daemon liveness dead, so `reap_main` will take the both-dead unlink shortcut instead of the terminate branch.. Scenario: The harness would only prove that a dead row is unlinked, not that a recycled live owner survives the expired terminate path required by acceptance.
- **Proposed resolution**: Keep the row expired but leave daemon liveness live, or otherwise arrange for only one liveness check to fail before `reap_main` reaches termination.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: security
- **Location**: scripts/test-bgjob.sh
- **Concern**: The cleanup traps are not required to revalidate process identity before killing the live recycled PID used in scenario 5.. Scenario: A raw PID or PGID teardown can signal the unrelated new owner after the assertion has already passed.
- **Proposed resolution**: Track the recorded identity for each started process and check it again in teardown, or exclude the recycled-owner PID from trap cleanup.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-bgjob.sh:scenario-5
- **Concern**: python/larch/bgjob/cli.py:122-124. Scenario: Harness scenario 5 pairs dead daemon with identity-mismatched child, but reap_main fast-unlinks when both liveness checks are false
- **Proposed resolution**: With daemon dead and child identity mismatch, child_liveness is false and daemon_liveness is false, so reap_main hits the both-dead unlink at cli.py:122-124 and never reaches terminate_validated_process_group at 126-132; the harness can pass while skipping the terminate branch the plan requires Revise scenario 5: either use an expired row where daemon_liveness stays true via a live decoy identity while child fields point at a recycled PID with corrupted identity, or drop the harness terminate-branch requirement and prove no-signal on the both-dead fast-unlink path while leaving terminate coverage to test_reap.py case 2

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: scripts/test-bgjob.sh:scenario-2
- **Concern**: Owner-death wait loop should budget for BGJOB_OWNER_VALIDATION_FAILURE_THRESHOLD. Scenario: Owner death needs three consecutive owner validation failures before the grace timer starts; a wait budget that only covers grace plus one poll can still flake on slower runners
- **Proposed resolution**: Pin an explicit wait budget in scenario 2: at least three poll intervals at the overridden poll rate, plus the overridden grace window, plus small slack; fail with diagnostics if BGJOB_RC=orphaned is not observed in time schema_version scope severity focus_area location what scenario_or_breakage suggested_fix

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-bgjob.sh:scenario-5 python/larch/bgjob/cli.py:122-132
- **Concern**: Harness scenario 5 fixture cannot reach the terminate branch it targets. Scenario: Plan scenario 5 sets daemon liveness dead and child identity mismatched on a live recycled PID. child_liveness is false on mismatch and daemon_liveness is false when the daemon is dead, so reap_main satisfies (not child_live.live and not daemon_live.live) and fast-unlinks at cli.py:122-124 without calling terminate_validated_process_group at 126-132. The harness can still pass the no-signal check while missing the terminate branch FINDING_3 aimed to exercise
- **Proposed resolution**: Revise scenario 5 preconditions: for terminate-path proof use an expired row with daemon_liveness still true (record a still-live decoy daemon identity) and child_liveness false via corrupted child fields on the recycled PID; or accept the both-dead fast-unlink path for harness no-signal proof and leave terminate coverage to test_reap.py case 2 only

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:30-38,51,172-175
- **Concern**: Real-process reap scenario still deadens the daemon, so it only exercises the both-dead unlink shortcut and never proves the terminate-validated recycled-PID path.. Scenario: Acceptance criterion 1 can pass while `terminate_validated_process_group` regresses and the no-signal guarantee for a live recycled PID stays untested.
- **Proposed resolution**: Keep the daemon alive for scenario 5, force expiry, and use the live recycled child mismatch to drive `reap_main` through the terminate branch before unlinking.

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: plan.txt:69-79,181
- **Concern**: The new override helpers only read env inside the monitor loop, so an invalid test-only override will surface after `bgjob start` has already printed STARTED and registered the job.. Scenario: That violates the plan's fail-closed-at-startup contract and can leave a stale registry row if the env is malformed.
- **Proposed resolution**: Add a preflight parse before the child registers or prints STARTED, while keeping the call-time reads in `_check_owner_validation` and `_monitor`.

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-bgjob.sh:planned scenario 5; python/larch/bgjob/cli.py:119-132
- **Concern**: Planned recycled-PID harness fixture still misses the terminate branch. Scenario: The plan tells scenario 5 to make DAEMON_PID absent or identity-invalid. An absent daemon makes read_entry return None; a dead daemon plus child identity mismatch satisfies the both-dead fast unlink before terminate_validated_process_group runs. The real-process harness can pass without exercising the recycled-PID no-signal path required by work item A.
- **Proposed resolution**: Make scenario 5 keep daemon_liveness live=True with a harness-owned placeholder daemon identity, force expiry and no result env, and corrupt only the recorded CHILD_* identity for the live recycled PID so reap reaches the expired terminate branch and proves the PID is not signaled.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-bgjob.sh:scenario-5
- **Concern**: Harness scenario 5 still routes through both-dead fast unlink, not the expired terminate branch. Scenario: `reap_main` checks `result or (not child_live.live and not daemon_live.live)` before `entry_expired` (`python/larch/bgjob/cli.py:122-126`). With daemon dead and a live recycled PID whose recorded child identity mismatches, both `child_liveness` and `daemon_liveness` are false (`python/larch/bgjob/registry.py:162-173`). Reap unlinks at 122-124 and never calls `terminate_validated_process_group`, so the harness can pass while failing to prove the no-signal terminate path the plan and issue require
- **Proposed resolution**: In scenario 5, keep an identity-valid live daemon (or otherwise ensure `daemon_liveness.live=true`), force expiry via old `START_EPOCH` or small `BUDGET_S`, point `CHILD_PID` at a live recycled process with mismatched recorded child identity, then assert the row is removed and the recycled PID survives. Align with pytest case 2 preconditions and the plan note that scenario 5 must use the expired terminate branch, not the both-dead shortcut alone ### 1. [correctness] `scripts/test-bgjob.sh` scenario 5 — wrong reap branch **Concern:** Scenario 5 specifies daemon dead plus a live recycled child PID with mismatched identity. That makes both liveness checks false, so `reap_main` takes the fast unlink at `python/larch/bgjob/cli.py:122-124` and never reaches the expired terminate path at lines 126-132. The harness can still pass (no signal sent) without exercising the terminate-validated no-signal guarantee the plan calls out in failure modes and edge cases. **Suggested revision:** Keep daemon identity-valid and live, force row expiry, use a live recycled child PID with corrupted recorded child identity fields, then assert row removal and that the recycled process survives. Match the pytest case 2 shape: expired row, `daemon_liveness` true, `child_liveness` false.

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-bgjob.sh (plan.txt:30-38; python/larch/bgjob/cli.py:114-132)
- **Concern**: Recycled-PID reap fixture cannot reach the intended terminate branch. Scenario: The plan tells the harness to make daemon liveness dead or absent while the child identity is mismatched. If DAEMON_PID is absent, registry.read_entry returns None and reap takes the invalid-row unlink path. If daemon liveness is false and child liveness is false, reap takes the both-dead fast unlink before entry_expired. Either path can pass the row-removed and live-PID assertions without proving the expired terminate-path no-signal guarantee.
- **Proposed resolution**: Change scenario 5 to keep a live identity-valid daemon record, keep the row expired, and make only the recorded child identity mismatch the live recycled PID. Then assert reap unlinks the row and the recycled PID remains live after terminate_validated_process_group rejects the recorded child identity.

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-bgjob.sh (plan.txt:22-24)
- **Concern**: Budget-expiry scenario only checks the timeout result, not that the child group was killed. Scenario: The required real-process scenario says budget expiry kills the group and writes BGJOB_RC=timeout. A daemon bug could write BGJOB_RC=timeout while leaving the long child running; the planned harness would still pass and cleanup would hide the leaked process.
- **Proposed resolution**: Capture the child pid or recorded identity from the registry before waiting, then after BGJOB_RC=timeout assert the recorded child or process group is no longer live before cleanup runs.
