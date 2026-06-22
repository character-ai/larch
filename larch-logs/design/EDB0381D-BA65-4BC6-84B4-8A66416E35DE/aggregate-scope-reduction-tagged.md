### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/lint_consecutive_bash.py:29-34,79-83
- **Concern**: [SCOPE-REDUCTION] Listed pause/recovery/task-notification carve-outs lack detection rules. Scenario: Implementer may build broad body-pattern auto-carve-outs beyond WRONG/CORRECT, expanding scope and hiding smells the issue targets; tests only need fixture coverage
- **Proposed resolution**: Treat WRONG/CORRECT as the only automatic carve-out; document pause/resume, recovery-probe, and immediate-background boundaries as first-run suppression categories, not pattern matchers in the linter
