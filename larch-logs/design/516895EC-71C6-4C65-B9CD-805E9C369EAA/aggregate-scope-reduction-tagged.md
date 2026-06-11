### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:789-817
- **Concern**: [SCOPE-REDUCTION] Exhaustive smoke matrix exceeds D3 acceptance. Scenario: Implementer may spend time wiring or running branch smokes for verbal issues, OOS partial failures, and validator choices even though static lint, focused wrapper checks, one end-to-end smoke, pause/resume, and degraded gate satisfy the issue
- **Proposed resolution**: Trim required testing to test-design-structure, relevant-checks, focused wrapper checks, one /design smoke, pause/resume, and degraded one-down and both-down checks; leave branch-specific smokes optional
