### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/bgjob/test_bgjob_cli.py
- **Concern**: [SCOPE-REDUCTION] Firm `test_bgjob_cli.py` owner-fallback test duplicates existing daemon coverage. Scenario: `python/tests/bgjob/test_daemon.py` already has `test_owner_identity_from_env_uses_session_pid_env`, which pins empty `--owner-pid` resolving through `LARCH_CLAUDE_PID`; adding a parallel `start_main` capture test grows diff without new failure signal for #6591
- **Proposed resolution**: Drop the mandated `test_bgjob_cli.py` addition; keep owner fallback pinned by the existing daemon test and extend `test_step7a_bgjob_launch_starts_transport` (the plan's `MAY_UPDATE` path) to assert launch argv omits `--owner-pid`

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-ship.sh:309-316
- **Concern**: [SCOPE-REDUCTION] Step 8 bgjob start omits --sentinel. Scenario: Plan asks every launcher case to assert sentinel shape, but step-8-ship.sh only passes --merge-result-env before the -- separator; a shared sentinel assertion will fail or force a wrong edit to step-8-ship.sh
- **Proposed resolution**: Per-launcher assertion table: require --sentinel only for step3/step5/step5-resume/step6; for step8 assert owner-pid and merge-result-env only

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/bgjob/test_bgjob_cli.py
- **Concern**: [SCOPE-REDUCTION] Proposed CLI owner-fallback test duplicates daemon coverage. Scenario: test_owner_identity_from_env_uses_session_pid_env in python/tests/bgjob/test_daemon.py:132-147 already pins LARCH_CLAUDE_PID fallback when --owner-pid is absent; test_step7a_bgjob_launch_starts_transport already shows Step 7a omits explicit --owner-pid
- **Proposed resolution**: Demote the new test_bgjob_cli.py case to MAY_UPDATE; extend test_step_7a.py only if Step 7a argv contract needs an explicit no --owner-pid assertion
