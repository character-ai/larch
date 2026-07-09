### [Plan Review] FINDING_2

### FINDING_2: New TOCTOU cases need per-case reset or documented ordering
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The new race-variant tests do not pin execution order or reset `$TMPDIR/larch-read-poll` for each case, so a symlink layout left behind by one variant can leak into the next and make the harness flaky.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Append the new TOCTOU block after the parent symlink test, or require each new case to reset `$TMPDIR/larch-read-poll` in its own setup (and document that order in the test file header).

