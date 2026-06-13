## Decision 1: dispatch-panel.sh cutover scope
- **Question**: Should `skills/review/scripts/dispatch-panel.sh` be updated to call the Python CLI verb (since it calls `scout-dynamic-archetypes.sh`, which is absorbed)?
- **Resolution**: Yes — include `dispatch-panel.sh` in the call-site cutover. The `/review` path cutover is in scope for this issue.
- **Source**: user
