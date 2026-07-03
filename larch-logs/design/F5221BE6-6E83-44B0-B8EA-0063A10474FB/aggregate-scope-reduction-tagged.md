### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_ship.py:340-349
- **Concern**: [SCOPE-REDUCTION] ship route-exit still trusts expanded --json-file paths. Scenario: Plan hardens only --implement-tmpdir. The Step 8 fence keeps --json-file "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json", which a fresh shell expands to /.step-8-ship-handoff.json even after implement-run exports IMPLEMENT_TMPDIR, because argv is fixed before exec. route-exit then reads the wrong file and Step 8+ routing fails after a real ship notification.
- **Proposed resolution**: Drop --json-file from the route-exit fence and rely on the existing default implement_tmpdir/.step-8-ship-handoff.json, or ignore unreadable json-file values that are not under the resolved implement tmpdir.
