### FINDING_1: Preserve backlog-nudge failure behavior
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The backlog-nudge path must catch `ShipError` and preserve its existing advisory failure exit and stderr behavior, rather than allowing an uncaught traceback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `audit_runs.py` plan text, add an explicit backlog-nudge rule: catch `ShipError` (and preserve the existing invalid-JSON stderr) inside `_bugs_backlog_nudge_issue_rows`, return `None`, and keep exit `1` behavior. Extend `test_audit_runs.py` wrapper mocks to assert that path, not only preflight empty-list coercion.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

