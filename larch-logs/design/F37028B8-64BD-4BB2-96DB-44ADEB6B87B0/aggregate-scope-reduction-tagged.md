### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/ci_monitor.py:1472-1493; python/larch/implement/ship_merge.py:285-349
- **Concern**: [SCOPE-REDUCTION] Warning-triggered fail-closed refresh would treat intentional --no-logs-commit as a push blocker. Scenario: `--no-logs-commit` is a public flag that suppresses larch-log flush commits, and `_pre_push_probe` returns `no-logs-commit`; the planned "any skip blocks push" rule would stall CI-fix or post-ensure pushes even though the operator explicitly disabled committed logs.
- **Proposed resolution**: Exempt `REFRESH_SKIP_NO_LOGS_COMMIT` from warning-triggered fail-closed blocking, warn if useful, and keep fail-closed behavior for real refresh failures such as recovery or commit failure.

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
