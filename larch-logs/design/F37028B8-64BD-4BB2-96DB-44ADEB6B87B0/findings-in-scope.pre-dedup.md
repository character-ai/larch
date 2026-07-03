### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/ci_monitor.py:1472-1493; python/larch/implement/ship_merge.py:285-349
- **Concern**: [SCOPE-REDUCTION] Warning-triggered fail-closed refresh would treat intentional --no-logs-commit as a push blocker. Scenario: `--no-logs-commit` is a public flag that suppresses larch-log flush commits, and `_pre_push_probe` returns `no-logs-commit`; the planned "any skip blocks push" rule would stall CI-fix or post-ensure pushes even though the operator explicitly disabled committed logs.
- **Proposed resolution**: Exempt `REFRESH_SKIP_NO_LOGS_COMMIT` from warning-triggered fail-closed blocking, warn if useful, and keep fail-closed behavior for real refresh failures such as recovery or commit failure.



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



### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/report/run_log_manifest.py:601-625; skills/implement/SKILL.md:145-150
- **Concern**: [SCOPE-REDUCTION] Warning fail-closed handling treats intentional no-logs skip as a hard push block. Scenario: --no-logs-commit is an existing public flag that suppresses larch-log flush commits. With the plan's any-skip fail-closed rule, a guideline warning under --no-logs-commit makes flush_logs_pre return no-logs-commit and stalls instead of respecting the explicit no-logs mode.
- **Proposed resolution**: Exempt REFRESH_SKIP_NO_LOGS_COMMIT from the warning-triggered hard block in both refresh seams; keep the stderr warning and proceed because that mode intentionally has no committed log target.



### FINDING_5:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/ci_monitor.py:1403-1515; python/larch/implement/ship_merge.py:282-330
- **Concern**: [SCOPE-REDUCTION] Warning-triggered fail-closed refresh treats intentional no-logs-commit skips as push-blocking failures. Scenario: The plan says any warning-triggered flush skip or failure returns not-pushed or stalled. With /implement --merge --no-logs-commit, flush_logs_pre returns no-logs-commit from the existing no_logs_commit contract, so a guideline warning would block the existing CI-fix or post-ensure push even though the operator explicitly disabled committed log updates.
- **Proposed resolution**: Keep fail-closed behavior for real refresh failures, but explicitly allow config.REFRESH_SKIP_NO_LOGS_COMMIT to preserve the existing no-logs-commit push and merge behavior. Add a focused assertion for that exemption at the new CI-fix or post-ensure seam.



