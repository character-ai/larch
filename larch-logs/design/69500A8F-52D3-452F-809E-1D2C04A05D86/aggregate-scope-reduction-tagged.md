### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:59-66
- **Concern**: [SCOPE-REDUCTION] Fail-closed when stdout POSTPLAN rows are missing but internal postplan already completed. Scenario: Durable `.design-postplan-emit-result.env` plus step-2b.5 prove success; fail-closed aborts valid `/design` runs after stdout capture loss only
- **Proposed resolution**: When step-2b.5 exists, read `.design-postplan-emit-result.env` to bind `_postplan_rc`/`_postplan_status` and continue; skip only the second postplan fence
