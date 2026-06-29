### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:39-43
- **Concern**: [SCOPE-REDUCTION] Safe-edits list leaves an exception for fenced Bash block changes. Scenario: This is a prose-only compression task, but the exception can let implementation touch Bash fences when nearby prose changes, which risks launcher or sentinel contract drift outside the feature scope
- **Proposed resolution**: Make the rule unconditional: keep fenced Bash blocks byte-stable and edit only prose outside fences
