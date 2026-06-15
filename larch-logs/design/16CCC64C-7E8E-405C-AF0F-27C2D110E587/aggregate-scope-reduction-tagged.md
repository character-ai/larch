### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: .claude/rules/skill-editing-trace.md:2
- **Concern**: [SCOPE-REDUCTION] Implement fence-harness note is planned inside skill-editing-trace, whose paths glob all skills/**/SKILL.md. Scenario: The new EXPECTED_OLD/EXPECTED_NEW reminder will inject on design/review/research SKILL edits where it does not apply, diluting a cross-skill trace rule and missing the tighter implement-only trigger the bug needs
- **Proposed resolution**: Create a dedicated rule (for example implement-fence-shape-harness.md) with paths scoped to skills/implement/SKILL.md and scripts/test-implement-fence-shape.sh instead of extending skill-editing-trace.md
