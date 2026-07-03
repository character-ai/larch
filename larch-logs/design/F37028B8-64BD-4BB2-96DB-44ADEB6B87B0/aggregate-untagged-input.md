### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:453-496
- **Concern**: PR-creation warning flush is wired only into the merge-only post-ensure push. Scenario: For /implement without --merge, draft, or forked PR creation, _pin_and_load_guidelines_note can append the scoped guideline-drop warning, then run_ship returns through _complete_pr_created_without_merge before _post_ensure_flush_and_push runs. The warning still remains only in the temp execution-issues.md, so the proposed PR-creation fix is incomplete for a supported ship-pr path.
- **Proposed resolution**: Route pin_warning_logged through the non-merge PR-created return path too. Flush and push before returning when the warning was logged, or move the warning-producing pin/load step to a point before an existing guaranteed log flush and branch push for every PR-created outcome.

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:453-496
- **Concern**: Pin-warning refresh is wired only through the merge-only post-ensure path. Scenario: The plan sends pin_warning_logged to _post_ensure_flush_and_push, but ship.py returns through _complete_pr_created_without_merge for non-merge, draft, forked, forked-target, or repo-unavailable runs before that helper. A guideline warning logged during _pin_and_load_guidelines_note on those PR-created paths still remains only in the temp execution-issues.md.
- **Proposed resolution**: Flush when pin_warning_logged is true before pr.ensure_pr so the warning rides ensure_pr's existing branch push, or thread equivalent warning refresh handling into the non-merge completion path.
