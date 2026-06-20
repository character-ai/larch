### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:46
- **Concern**: [SCOPE-REDUCTION] Item 1 doc work largely duplicates existing NEVER #8 carve-out text. Scenario: NEVER #8 already states implement has no terminal sentinels, forbids design sentinel probes, and calls foreground probing a `/design`-only carve-out; adding three more bullets risks redundant NEVER growth without new operator signal
- **Proposed resolution**: Add at most one short intentional-asymmetry clause (not a contradiction) if the anti-polling harness still needs a new pinned literal; do not restate the existing carve-out sentences
