### FINDING_2: Step 8 handoff commands still depend on fresh-shell IMPLEMENT_TMPDIR
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: The Step 8 handoff probe and stale-handoff clear are still executed as direct shell fences, so a fresh shell can expand `"$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"` to `/.step-8-ship-handoff.rc` and either miss a completed ship or touch the wrong file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Route both operations through implement-run-$PPID.sh via a tiny wrapper script, or document and test a one-line pointer-based probe that does not require exported IMPLEMENT_TMPDIR.
  - From Cursor-Pragmatic: Resolve tmpdir from `current-implement-env-$PPID.sh` (same pointer the new runner uses) in those two commands, or route them through a one-line helper invoked via `implement-run-$PPID.sh`.


### FINDING_7:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_ship.py:340-349
- **Concern**: [SCOPE-REDUCTION] ship route-exit still trusts expanded --json-file paths. Scenario: Plan hardens only --implement-tmpdir. The Step 8 fence keeps --json-file "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json", which a fresh shell expands to /.step-8-ship-handoff.json even after implement-run exports IMPLEMENT_TMPDIR, because argv is fixed before exec. route-exit then reads the wrong file and Step 8+ routing fails after a real ship notification.
- **Proposed resolution**: Drop --json-file from the route-exit fence and rely on the existing default implement_tmpdir/.step-8-ship-handoff.json, or ignore unreadable json-file values that are not under the resolved implement tmpdir.


