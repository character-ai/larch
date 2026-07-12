### FINDING_2: Clear bail overlays during manual-merge reconciliation
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: Reconciliation may leave stale bail-state keys, allowing a verified merged run to normalize back to `bailed-needs-user-input`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Name the bail keys reconcile must clear on all three layers (`BAIL_NEEDS_USER_INPUT`, `BAIL_REASON`, `BAIL_FAILURE_DETAIL_LOG`, etc.) or reuse the same terminal `phase=done` field set as `ship_state._write_ship_state`; post-read verification must fail if any bail overlay remains


