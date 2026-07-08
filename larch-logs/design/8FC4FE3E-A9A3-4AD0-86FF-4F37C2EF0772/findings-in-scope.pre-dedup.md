### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/bgjob/test_bgjob_cli.py
- **Concern**: [SCOPE-REDUCTION] Firm `test_bgjob_cli.py` owner-fallback test duplicates existing daemon coverage. Scenario: `python/tests/bgjob/test_daemon.py` already has `test_owner_identity_from_env_uses_session_pid_env`, which pins empty `--owner-pid` resolving through `LARCH_CLAUDE_PID`; adding a parallel `start_main` capture test grows diff without new failure signal for #6591
- **Proposed resolution**: Drop the mandated `test_bgjob_cli.py` addition; keep owner fallback pinned by the existing daemon test and extend `test_step7a_bgjob_launch_starts_transport` (the plan's `MAY_UPDATE` path) to assert launch argv omits `--owner-pid`



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-5-resume.sh:217
- **Concern**: Plan mislabels step5-resume slug as dynamic `$STEP`. Scenario: `STEP` is hardcoded to `implement-step5-resume`; following the plan text could make the parametrized launcher test overfit a nonexistent dynamic slug or miss the static assertion
- **Proposed resolution**: In the `step5-resume` parametrization row, treat `implement-step5-resume` as a fixed expected slug (same pattern as step5-review), not a dynamic `$STEP` variable



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-ship.sh:309-316
- **Concern**: [SCOPE-REDUCTION] Step 8 bgjob start omits --sentinel. Scenario: Plan asks every launcher case to assert sentinel shape, but step-8-ship.sh only passes --merge-result-env before the -- separator; a shared sentinel assertion will fail or force a wrong edit to step-8-ship.sh
- **Proposed resolution**: Per-launcher assertion table: require --sentinel only for step3/step5/step5-resume/step6; for step8 assert owner-pid and merge-result-env only



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-5-resume.sh:217
- **Concern**: Plan mislabels step5-resume STEP as dynamic. Scenario: $STEP is hardcoded to implement-step5-resume at line 217, so a dynamic-slug test could assert the wrong contract or overfit argv-derived step names
- **Proposed resolution**: Assert the literal slug implement-step5-resume in the step5-resume parametrization row



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/bgjob/test_bgjob_cli.py
- **Concern**: [SCOPE-REDUCTION] Proposed CLI owner-fallback test duplicates daemon coverage. Scenario: test_owner_identity_from_env_uses_session_pid_env in python/tests/bgjob/test_daemon.py:132-147 already pins LARCH_CLAUDE_PID fallback when --owner-pid is absent; test_step7a_bgjob_launch_starts_transport already shows Step 7a omits explicit --owner-pid
- **Proposed resolution**: Demote the new test_bgjob_cli.py case to MAY_UPDATE; extend test_step_7a.py only if Step 7a argv contract needs an explicit no --owner-pid assertion



### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/bgjob/test_bgjob_cli.py
- **Concern**: CLI owner-fallback test setup clears the wrong env vars. Scenario: `owner_identity_from_env` prefers `LARCH_BGJOB_OWNER_PID` and `CLAUDE_PID` before `LARCH_BGJOB_OWNER_PID` is checked first; only then `LARCH_CLAUDE_PID`. The plan says to clear lower-priority vars. A test that leaves `LARCH_BGJOB_OWNER_PID` set can pass while never exercising the Step 7a `LARCH_CLAUDE_PID` fallback.
- **Proposed resolution**: In the planned `cli.start_main` test, unset or clear `LARCH_BGJOB_OWNER_PID`, `CLAUDE_PID`, and `LARCH_BG_POLL_GUARD_SESSION_PID`, then set `LARCH_CLAUDE_PID=12345`. Mirror `test_owner_identity_from_env_fails_closed_without_session_pid` in `python/tests/bgjob/test_daemon.py`.



### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: Approach / Issue comment step
- **Concern**: Issue-comment body omits the #6595 daemon fix. Scenario: Issue scope requires correcting #6591 by recording harness-kill false-orphan root cause fixed via #6580 and #6595. The planned comment cites only the `LARCH_CLAUDE_PID` launcher path (#6580). It does not mention consecutive owner-validation failure threshold / grace hardening (#6595).
- **Proposed resolution**: The comment body should state Step 3 is covered by stable `LARCH_CLAUDE_PID` ownership (#6580) and daemon owner-validation hardening (#6595), with both pinned by the new regression tests (or cite existing daemon tests if unchanged).



