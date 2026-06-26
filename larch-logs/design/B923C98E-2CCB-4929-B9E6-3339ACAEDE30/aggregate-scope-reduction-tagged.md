### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: .claude/rules/topology-generation.md:28-36
- **Concern**: [SCOPE-REDUCTION] The plan ports orphaned CI-fix guidance into an existing path-triggered topology rule, expanding runtime prompt surface beyond the dead-reference deletion scope.. Scenario: The feature still ships correctly by deleting skills/shared/ci-fix-failure-patterns.md without replacement; the proposed rule edit preserves content that the issue identifies as no-loader shipped dead weight.
- **Proposed resolution**: Drop the .claude/rules/topology-generation.md update and delete skills/shared/ci-fix-failure-patterns.md without porting its contents.
