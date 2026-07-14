---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_2

### FINDING_2: Metric decreases can leave invalid or stale history
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Decreasing a metric does not define how history is updated, potentially leaving history above the current metric or causing pre-shrink bumps to trigger later gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify shrink behavior in the writer merge: on metric decrease, rewrite history to a single UTC seed at the new metric (or truncate trailing entries above the new metric) without requiring --reason. Add a test that shrink-only regen stays load-valid and that a later first increase is not treated as a second bump inside 14 days of pre-shrink history.


### [Plan Review] FINDING_3

### FINDING_3: Repeat-bump failures omit the file
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: Failure messages naming only the qualified symbol are ambiguous when the same symbol exists in multiple files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Include normalized file path in each repeat-bump failure line (for example file:qualified_symbol) while keeping code-tagged history and the three remediation exits.


---LARCH-REJECTED-END---
