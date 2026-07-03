### FINDING_1: Non-merge PR creation drops guideline warning
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The guideline-drop warning can be appended to the temp `execution-issues.md` during `_pin_and_load_guidelines_note`, but non-merge PR-created flows return through `_complete_pr_created_without_merge` before `_post_ensure_flush_and_push` runs. As a result, the warning can remain uncommitted on supported ship-pr paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: `Route pin_warning_logged through the non-merge PR-created return path too. Flush and push before returning when the warning was logged, or move the warning-producing pin/load step to a point before an existing guaranteed log flush and branch push for every PR-created outcome.`
  - From Codex-Pragmatic: `Flush when pin_warning_logged is true before pr.ensure_pr so the warning rides ensure_pr's existing branch push, or thread equivalent warning refresh handling into the non-merge completion path.`


