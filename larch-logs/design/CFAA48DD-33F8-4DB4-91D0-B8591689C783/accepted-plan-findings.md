### FINDING_3: Repoint public design references to shared readability path
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The public `/design` reference updates still leave some counted MANDATORY anchors on the deleted design-scoped readability path, so the move to the shared file can remain only partially repointed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In each listed reference `### UPDATED`, require repoint to `` `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.** `` in every MANDATORY anchor, not just a shared file move.
  - From Cursor-Requirements: Add the same repoint bullet as approval-gates: update the MANDATORY line to `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md` with the counted `.**` suffix.


