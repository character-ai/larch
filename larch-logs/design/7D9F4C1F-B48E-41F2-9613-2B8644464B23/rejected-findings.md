### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:9; skills/*/SKILL.md:3; .claude/skills/*/SKILL.md:3
- **Concern**: The plan compresses only 14 over-cap descriptions, but the scope anchor asks to compress all 28 skill description fields.. Scenario: The PR would leave half of the Tier-1 registry descriptions uncompressed, so the stated frontmatter compression goal is only partially delivered.
- **Proposed resolution**: Expand the plan to rewrite all 28 description values in scope, still only touching frontmatter, preserving Use when or Trigger when clauses, and keeping each value within the 200-char cap.

