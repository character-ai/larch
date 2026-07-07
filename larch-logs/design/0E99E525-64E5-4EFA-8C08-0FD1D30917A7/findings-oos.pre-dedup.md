### OOS_1: Unreachable evaluate_failure prefetch remains after non-pending simplification
- **Description**: Unreachable evaluate_failure prefetch remains after non-pending simplification. Scenario: Once ci_fix_rebase_pending=false returns immediate handoff the upfront log download and transient rerun block becomes dead code that still couples evaluate_failure to deleted agentic-fix semantics
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/ci_monitor.py:1838-1891
- **Phase**: design



### OOS_2: CI_FIXABLE_JOBS static allowlist contradicts new fixer prompt
- **Description**: CI_FIXABLE_JOBS static allowlist contradicts new fixer prompt. Scenario: The fixer prompt forbids static job allowlists but classify_failed_jobs still gates on CI_FIXABLE_JOBS which the issue cites as a reason the old fixer failed
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/ci_monitor.py:946-949
- **Phase**: design



### OOS_3: No timing task-kind for native Agent CI fixer spans
- **Description**: No timing task-kind for native Agent CI fixer spans. Scenario: Plan item 9 adds a Step 8 - CI fixer mark but TIMING_TASK_KINDS_ALLOWED has no claude-ci-fixer style entry so record-vendor-task may warn and /report-tokens may omit vendor rows if Agent usage is not sidecar-ingested
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/timing.py:21-45
- **Phase**: design



