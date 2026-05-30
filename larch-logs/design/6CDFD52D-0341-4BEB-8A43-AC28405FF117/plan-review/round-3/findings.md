### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:889-901
- **Concern**: Plan adds Item C coverage in test-ship-pr.sh but does not say how to hit append_tool_failure_local fallback. Scenario: Default make_repo leaves append-tool-failure.sh executable and IMPLEMENT_TMPDIR set, so a test that only calls ship-pr with a control-byte output_file exercises the --redact success path (append-tool-failure.sh), not the larch_err relay loops being changed
- **Proposed resolution**: Spell out the fixture: force [ -z "$log_tmpdir" ] or [ ! -x "$SCRIPT_DIR/append-tool-failure.sh" ] (e.g. empty read_state tmpdir or non-executable helper), capture stderr, assert BEL/ESC stripped; mirror test-ci-failed-jobs.sh T8 printf pattern

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/test-collect-findings.sh:30-37
- **Concern**: Plan adds collector/wait log relay assertions but not a stderr capture contract. Scenario: Harness captures stdout only via out=$(...); collect-findings.sh runs larch_quiet_init and failure relays use larch_err on stderr, so a stdout-only grep can pass while control bytes still appear on stderr
- **Proposed resolution**: Require merged 2>&1 capture or LARCH_QUIET_DISABLE=1 for the new case(s); assert captured stderr lacks \x07/\x1b while preserving printable text (same pattern as scripts/test-ci-failed-jobs.sh:178-194)
