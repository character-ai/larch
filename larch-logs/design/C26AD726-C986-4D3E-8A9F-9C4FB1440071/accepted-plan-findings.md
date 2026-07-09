### FINDING_1: Stale anti-polling companion doc pins retired literals
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The companion markdown for the deleted anti-polling harness still pins retired literals (`design-background-wait`, `task-notification`, and other removed contracts). After `scripts/test-implement-anti-polling-rule.sh` is deleted, that stale doc can keep the plan’s extinct-token grep failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Delete this companion doc with the harness, or rewrite it to describe only the bgjob-wait replacement contract


