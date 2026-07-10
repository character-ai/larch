### OOS_1: [SCOPE-REDUCTION] SECURITY.md appendix is not required to fix the statusline bug
- **Description**: [SCOPE-REDUCTION] SECURITY.md appendix is not required to fix the statusline bug. Scenario: The issue is stale-pointer lifecycle and run-scoped writers; symlink refusal and integrity behavior already live in `progress_file.py` and statusline code. A new SECURITY.md section adds doc churn without changing runtime behavior.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: SECURITY.md
- **Phase**: design



