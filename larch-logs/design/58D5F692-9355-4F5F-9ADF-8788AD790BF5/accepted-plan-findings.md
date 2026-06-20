### FINDING_8: Classification TSV schema docs still on old contract
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Classification TSV wire-schema docs stay on the old column contract. The plan appends `scope` to classification TSVs, but exact schema docs still advertise 21/22-column headers. Consumers of committed run logs and voting protocol docs can miss the new scope contract and mishandle OOS rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add docs/voting-process.md and docs/run-logs.md to the plan, and update the existing voting-protocol schema sentence with the new trailing scope column and counts.


