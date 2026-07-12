### FINDING_2: Plain issue-view command shape lacks wrapper coverage
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: major
- **Concern**: The audit identifies callers using plain `gh issue view <issue>` without `--json`, but the planned template wrapper and existing field helpers cover only JSON-based views. Without a plain-view wrapper, the stated view-shape coverage goal remains incomplete and future callers must retain raw issue-view construction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add a retrying plain-view wrapper for `gh issue view <issue>` with optional `repo` and `cwd`, or explicitly document and justify excluding these audited shapes from the coverage goal.
  - From Codex-Pragmatic: Add a minimal read wrapper for plain issue view, returning `CommandResult` through `_retry_read`, plus exact argv coverage


