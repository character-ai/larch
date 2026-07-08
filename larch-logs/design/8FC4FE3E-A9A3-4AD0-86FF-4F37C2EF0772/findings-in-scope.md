### FINDING_1: step5-resume slug should be a fixed literal, not dynamic `$STEP`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: minor
- **Concern**: The plan treats the `step5-resume` bgjob slug as dynamic via `$STEP`, but `skills/implement/scripts/step-5-resume.sh:217` hardcodes `STEP` to `implement-step5-resume`. A parametrized test that follows the plan’s dynamic-slug wording could overfit argv-derived step names or assert the wrong contract instead of pinning the static slug (same pattern as `step5-review`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the `step5-resume` parametrization row, treat `implement-step5-resume` as a fixed expected slug (same pattern as step5-review), not a dynamic `$STEP` variable
  - From Cursor-Innovation: Assert the literal slug implement-step5-resume in the step5-resume parametrization row

### FINDING_2: CLI owner-fallback test must clear higher-priority owner env vars
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The planned `cli.start_main` owner-fallback test setup may clear only lower-priority env vars. `owner_identity_from_env` checks `LARCH_BGJOB_OWNER_PID` and `CLAUDE_PID` before `LARCH_CLAUDE_PID`. If `LARCH_BGJOB_OWNER_PID` remains set, the test can pass without ever exercising the Step 7a `LARCH_CLAUDE_PID` fallback path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In the planned `cli.start_main` test, unset or clear `LARCH_BGJOB_OWNER_PID`, `CLAUDE_PID`, and `LARCH_BG_POLL_GUARD_SESSION_PID`, then set `LARCH_CLAUDE_PID=12345`. Mirror `test_owner_identity_from_env_fails_closed_without_session_pid` in `python/tests/bgjob/test_daemon.py`.

### FINDING_3: #6591 correcting comment should cite both #6580 and #6595 fixes
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: The planned issue-comment body for correcting #6591’s disposition cites only the stable `LARCH_CLAUDE_PID` launcher path (#6580). Issue scope requires recording that the harness-kill false-orphan root cause was fixed via both #6580 and #6595 (daemon owner-validation hardening). Omitting #6595 leaves the comment incomplete relative to the stated root-cause narrative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: The comment body should state Step 3 is covered by stable `LARCH_CLAUDE_PID` ownership (#6580) and daemon owner-validation hardening (#6595), with both pinned by the new regression tests (or cite existing daemon tests if unchanged).

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/bgjob/test_bgjob_cli.py
- **Concern**: [SCOPE-REDUCTION] Firm `test_bgjob_cli.py` owner-fallback test duplicates existing daemon coverage. Scenario: `python/tests/bgjob/test_daemon.py` already has `test_owner_identity_from_env_uses_session_pid_env`, which pins empty `--owner-pid` resolving through `LARCH_CLAUDE_PID`; adding a parallel `start_main` capture test grows diff without new failure signal for #6591
- **Proposed resolution**: Drop the mandated `test_bgjob_cli.py` addition; keep owner fallback pinned by the existing daemon test and extend `test_step7a_bgjob_launch_starts_transport` (the plan's `MAY_UPDATE` path) to assert launch argv omits `--owner-pid`

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-ship.sh:309-316
- **Concern**: [SCOPE-REDUCTION] Step 8 bgjob start omits --sentinel. Scenario: Plan asks every launcher case to assert sentinel shape, but step-8-ship.sh only passes --merge-result-env before the -- separator; a shared sentinel assertion will fail or force a wrong edit to step-8-ship.sh
- **Proposed resolution**: Per-launcher assertion table: require --sentinel only for step3/step5/step5-resume/step6; for step8 assert owner-pid and merge-result-env only

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/bgjob/test_bgjob_cli.py
- **Concern**: [SCOPE-REDUCTION] Proposed CLI owner-fallback test duplicates daemon coverage. Scenario: test_owner_identity_from_env_uses_session_pid_env in python/tests/bgjob/test_daemon.py:132-147 already pins LARCH_CLAUDE_PID fallback when --owner-pid is absent; test_step7a_bgjob_launch_starts_transport already shows Step 7a omits explicit --owner-pid
- **Proposed resolution**: Demote the new test_bgjob_cli.py case to MAY_UPDATE; extend test_step_7a.py only if Step 7a argv contract needs an explicit no --owner-pid assertion
