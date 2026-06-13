### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:410-414
- **Concern**: [SCOPE-REDUCTION] Plan targets nonexistent agents/heavy-worker.md. Scenario: The implementer may create or chase a new agent file outside the real heavy-worker reference path, adding scope and missing the actual contract location
- **Proposed resolution**: Remove this update block, or retarget it to skills/review/references/heavy-worker.md only if a stale retired-helper reference remains
