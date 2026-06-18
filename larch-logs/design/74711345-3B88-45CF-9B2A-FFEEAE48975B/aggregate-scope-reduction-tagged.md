### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/execution_issues.py:119-139
- **Concern**: [SCOPE-REDUCTION] Step 18 append-only flush must never call shared truncate branches. Scenario: Plan allows `--no-truncate` on shared `flush_execution_issues()`; today `already-flushed`, `no-records`, and `ok` all call `issue_log.write_text("")`. Guarding only the success path still clears stall-time Tool Failures on idempotent teardown replay.
- **Proposed resolution**: Prefer a dedicated `flush_execution_issues_safety_net()` mirroring bash `flush_execution_issues_safety_net()` (append via `run-log append` only). If a flag is kept, gate every `issue_log.write_text("", ...)` site.
