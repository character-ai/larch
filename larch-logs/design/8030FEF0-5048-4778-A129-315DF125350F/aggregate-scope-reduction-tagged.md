### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/run_logs.py:2637-2678
- **Concern**: [SCOPE-REDUCTION] New execution_issues.py duplicates existing append surface. Scenario: run_logs already exposes append_execution_issue and cli run-log append-entry; adding execution-issues append creates two append APIs and migration churn
- **Proposed resolution**: Port flush/refresh into run_logs (or execution_issues called only from run_logs) and retire run-log append-entry in the same cutover instead of a parallel module
