### FINDING_4: [OUT_OF_SCOPE] missing design smoke for shared phase-gantt rendering
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The over-cap coverage exercises `skill="implement"` only, so design final summaries that share `_render_phase_gantt` do not have a parallel regression check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Optional `skill="design"` smoke if you want symmetry; shared code makes the current gap low risk.

