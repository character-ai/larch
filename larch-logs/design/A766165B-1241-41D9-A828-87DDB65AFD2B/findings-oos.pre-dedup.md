### OOS_1:
- **Description**: [SCOPE-REDUCTION] `test_checks.py` edits are likely unnecessary churn. Scenario: Claude-first (`test_run_lint_fix_dispatches_claude_before_codex`) and Codex→Cursor fallback (`test_run_lint_fix_codex_fail_cursor_success`) tests already exist; plan only needs a read-only coverage audit
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/test_checks.py:1832-1951
- **Phase**: design

### OOS_2:
- **Description**: Optional `_wait_for_ci` parser tightening duplicates `_run_cycle` fail-closed rules. Scenario: Implementing both parser and caller changes adds two maintenance surfaces for the same stale-run bug
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/ci_agentic_fix.py:200-211
- **Phase**: design

### OOS_3:
- **Description**: Delegate timeout formula still budgets only one verify subprocess per cycle. Scenario: `verify_job_locally` runs once per fixable job; multiple jobs in one cycle can exceed `2 * SUBPROCESS_DEFAULT_TIMEOUT_SEC` even after the fix
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/ci_monitor.py:1456-1459
- **Phase**: design

