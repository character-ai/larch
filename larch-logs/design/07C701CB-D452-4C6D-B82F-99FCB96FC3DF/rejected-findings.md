### [Plan Review] FINDING_1

### FINDING_1: Bounded-root rule should cover all orchestrator grep probes
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The bounded-search-root guidance is scoped too narrowly to background probes. That leaves room for foreground or other orchestrator grep-family searches to keep using ascent-prone paths and scan above the intended root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the "Bounded search roots" subsection, state the rule for all orchestrator grep-family probes in Bash fences (or all such probes), not only background ones; keep the background stdin-blocking note separate from the parent-ascent ban


