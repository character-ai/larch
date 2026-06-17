### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step0-route.sh:101-121
- **Concern**: [SCOPE-REDUCTION] step0-route omits bash POSITIONAL_KIND re-validation block. Scenario: Invalid or stale POSITIONAL_KIND from parsed env can reach gh issue fetch or design route subprocess without the abort paths bash enforces today
- **Proposed resolution**: Mirror the issue/verbal/none/invalid case block from design-step0-route.sh in step0_route_main before issue fetch; add pytest for non-numeric issue positional and invalid POSITIONAL_KIND
