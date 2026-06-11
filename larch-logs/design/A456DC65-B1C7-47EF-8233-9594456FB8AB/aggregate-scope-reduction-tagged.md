### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/token-report.sh:349-394; scripts/token-report.md:21
- **Concern**: [SCOPE-REDUCTION] Plan replaces the current arbitrary non-Claude vendor JSON sibling contract with an undefined generic surface. Scenario: A vendor accepted by token record-vendor can lose its documented per_step/totals JSON object in token report output, which is a wire-surface regression from the current one sibling object per non-Claude vendor behavior
- **Proposed resolution**: Preserve the current dynamic sibling object for arbitrary non-Claude vendors, while keeping only codex cursor and claude_sub as ordered costed dedicated lanes
