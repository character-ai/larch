### OOS_1:
- **Description**: Plan duplicates terminal-outcome regex constants in Python while keeping `scripts/run-log-terminal-outcomes.inc.bash` as the bash source. Scenario: `verify_completeness_main` and `audit-scan-run.sh` can drift silently after edits to only one copy; false pass/fail on bail-signal checks
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/run_logs.py:61
- **Phase**: design

