### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/finalize.py:679-703
- **Concern**: [SCOPE-REDUCTION] Python kill_session_background_processes parity is not on the Step 18 production path. Scenario: /implement Step 18 always calls scripts/implement-finalize.sh teardown (skills/implement/scripts/step-18-finalize.sh:74); ship.py never calls finalize.teardown. The observed #4103 failure mode (launcher bash with $IMPLEMENT_TMPDIR/larch-run.sh in argv getting signaled) is fixed entirely in bash. Python changes plus python/test_finalize.py add diff without affecting the live teardown chain.
- **Proposed resolution**: Limit the kill-skip fix to scripts/implement-finalize.sh plus scripts/test-implement-finalize.sh; keep the ship.py breadcrumb only. Defer python/finalize.py ancestor work unless a caller wires finalize.teardown into production.
