### FINDING_1: Bounded-root rule should cover all orchestrator grep probes
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The bounded-search-root guidance is scoped too narrowly to background probes. That leaves room for foreground or other orchestrator grep-family searches to keep using ascent-prone paths and scan above the intended root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the "Bounded search roots" subsection, state the rule for all orchestrator grep-family probes in Bash fences (or all such probes), not only background ones; keep the background stdin-blocking note separate from the parent-ascent ban

### FINDING_2: Preserve tier-1a size budget for the BASH_AUTHORING.md expansion
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The proposed BASH_AUTHORING.md addition risks pushing the file over its tier-1a line cap unless the plan explicitly budgets for the growth or validates the cap update.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a firm plan step to keep the BASH_AUTHORING.md edit line-neutral, or update TIER1A_LINE_CAPS with the intentional growth and include tier1a-size validation in the focused checks
