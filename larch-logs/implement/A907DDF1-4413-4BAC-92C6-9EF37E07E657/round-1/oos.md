### FINDING_1: [OUT_OF_SCOPE] lifecycle prefix literals remain outside composition AST contexts
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `python/larch/implement/preflight.py:21-28` — `LIFECYCLE_PREFIXES` still embeds raw `[DESIGNING]`, `[DONE]`, etc. tuple literals outside compare/match/composition AST contexts, so L1 does not ratchet that writer surface. That predates this branch and matches the plan’s narrow composition scope, not a regression from this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false
