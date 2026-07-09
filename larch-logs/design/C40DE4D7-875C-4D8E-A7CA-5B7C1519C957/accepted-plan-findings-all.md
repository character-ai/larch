### FINDING_3: Recycled-PID reap harness needs an expired stale-row fixture
- **Reviewer(s)**: Cursor-Arch, Codex-dyn-Process Reap Safety
- **Severity**: major
- **Concern**: The real-process `bgjob reap` scenario for a recycled PID can miss the intended branch unless the synthetic row is actually stale or expired. If the fixture only corrupts child identity without forcing the dead/expired path, the harness can fall through unlink behavior and fail to prove the no-signal guarantee for the recycled PID's new owner.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `State explicitly that the synthetic row must have a dead daemon and no result env (or an expired entry) while CHILD_PID points at a live recycled process with mismatched identity fields. Keep the expired plus terminate_validated mismatch path in python/tests/bgjob/test_reap.py.`
  - From Codex-dyn-Process Reap Safety: `Set START_EPOCH old enough or BUDGET_S small enough that the row is definitely expired before bgjob reap runs, then assert the live PID still survives.`


### FINDING_4: PR #6706 still needs the Section E table in its body
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: Recording the Section E disposition table only in committed docs does not satisfy the acceptance criterion that still requires the table in PR #6706's description. A run can follow the plan and still leave the literal PR-body requirement unmet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: `Add the explicit gh pr edit 6706 --body-file ... step, or revise the scope to state that the docs subsection is the accepted replacement.`
  - From Cursor-Innovation: `Either add an explicit plan step to update PR #6706 (or amend the tracking issue acceptance criteria with operator sign-off), or document in the plan/issue that committed docs are the canonical substitute and close the AC mismatch before ship.`
  - From Codex-Innovation: `Add an explicit gh pr edit 6706 --body-file ... step, or equivalent PR-body mutation, in addition to the docs entry.`
  - From Cursor-Requirements: `Reconcile the contract: either add an explicit plan step to update the issue acceptance criteria to the docs-in-new-PR delivery, or add the minimal gh pr edit 6706 step if AC4 must stay literal.`
  - From Codex-Requirements: `Remove the docs-as-replacement language and add an implementation step to update PR #6706's body with the Section E table, using gh pr edit 6706 --body-file or an equivalent body-preserving flow; keep committed docs only if they do not replace the PR edit`


### FINDING_5: `reap_main` unit test case needs the terminate branch preconditions pinned
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Process Reap Safety
- **Severity**: minor
- **Concern**: The pytest case for a recycled PID needs an expired row with daemon liveness still true and child liveness false so `reap_main` reaches the terminate branch. If both liveness checks are false, the fast unlink path can bypass the intended terminate-validated-process-group behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: `State in the test plan that case 2 must keep at least one liveness true (typically daemon_live) while entry_expired is true and terminate_validated_process_group returns a non-`missing-pid` mismatch verdict.`
  - From Cursor-Requirements: `In item 2, specify daemon_liveness live=True and child_liveness live=False (identity mismatch) on an expired entry so reap reaches python/larch/bgjob/cli.py:126-132; keep the bash harness scenario 5 on the both-dead unlink path`
  - From Cursor-dyn-Process Reap Safety: `In item 2, specify `daemon_liveness` live=True and `child_liveness` live=False (identity mismatch) on an expired entry so reap reaches `python/larch/bgjob/cli.py:126-132`; keep the bash harness scenario 5 on the both-dead unlink path`


### FINDING_6: Timing helper env reads must stay call-time, not import-time
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The timing helpers need to resolve env/config at call time instead of caching values at module import. Otherwise the existing monkeypatched orphan-timing tests stop affecting `_monitor`, even if the new parser tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: `Timing override helpers must resolve env/config at call time, not import time. Scenario: Plan requires existing monkeypatch.setattr(daemon.config, "BGJOB_OWNER_GRACE_S", 0.0) owner-grace tests to keep working. Helpers that parse env once at module import cache the production default; monkeypatching the constant afterward no longer affects _monitor, breaking orphan timing tests while the new parser tests still pass.`


### FINDING_7: Env-via-config baseline regeneration needs a reason path for new reads
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: Adding the new test-only env reads without a documented reason path can make the env-via-config-constant baseline regen fail closed. That leaves the lint/regeneration step incomplete until the read-site reasons are supplied.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: `Add an explicit baseline step: record per-read reasons via # lint-env-via-config-constant: ok test-only bgjob timing override at each read site, or document a one-shot python3 python/cli.py lint env-via-config-constant --write --initial-reason ... invocation before make regen-env-via-config-constant-baseline.`


### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:3,128-133,148
- **Concern**: [SCOPE-REDUCTION] Plan replaces the required PR #6706 body edit with a committed docs update. Scenario: Acceptance criterion 4 remains unmet because the Section E table would land in the new PR/docs, not in PR #6706's description; the docs change also adds shipped repo scope the issue did not request
- **Proposed resolution**: Drop the docs/workflow-lifecycle.md update and add a firm non-file step to run gh pr edit 6706 --body-file ... and verify PR #6706's body contains the table

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


### FINDING_5: Budget-expiry test does not prove the child group was killed
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The budget-expiry scenario only checks for `BGJOB_RC=timeout`, so it can pass even if the daemon reports timeout but leaves the long-running child or process group alive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Capture the child pid or recorded identity from the registry before waiting, then after BGJOB_RC=timeout assert the recorded child or process group is no longer live before cleanup runs

