### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:405,698; scripts/test-design-structure.sh:248-249
- **Concern**: Gate A/B settle-dispatch hedge can stale exact structure harness. Scenario: The plan requires adding an already-loaded hedge to the SKILL.md settle-dispatch reads, but test-design-structure asserts the old item-1 line followed immediately by item 2 for both SKILL call sites. make lint can fail after the required prose change.
- **Proposed resolution**: Add scripts/test-design-structure.sh to the plan and update the two SKILL settle-dispatch adjacency literals to the hedged item-1 text.
