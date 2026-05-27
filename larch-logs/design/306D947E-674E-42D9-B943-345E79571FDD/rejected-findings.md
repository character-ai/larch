### [Plan Review] FINDING_2

### FINDING_2: File-level counts can miss per-step directive regressions
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Switching orchestrator-inline enforcement to a file-level count does not protect each required per-step or per-block composition site. A removed directive in one step and a duplicate in another could preserve the expected total while still leaving a required site stale or absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Keep the SIMPLE scope but encode the four SKILL.md directive sites as distinct expected contexts or lightweight per-block anchors instead of only a file-level total; keep one-count rows for single-directive reference files

