### FINDING_11: [OUT_OF_SCOPE] Decomposition marker composition
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-grammar-compat
- **Severity**: minor
- **Concern**: Decomposition marker handling still bypasses `issue_wire.compose_named_block`, so marker drift can continue on decomposition paths outside this migration scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-grammar-compat: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_12: [OUT_OF_SCOPE] Preflight blank-separated metadata test gap
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-grammar-compat
- **Severity**: minor
- **Concern**: The planned blank-separated `review_status`, `rounds_completed`, and `difficulty` regression fixtures are absent, leaving that compatibility path unguarded outside the current migration scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-grammar-compat: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_13: [OUT_OF_SCOPE] Drafter scout-manifest fence tracking
- **Reviewer(s)**: dyn-dyn-grammar-compat
- **Severity**: minor
- **Concern**: Scout-manifest detection in `python/larch/agents/_drafter.py` still uses a binary fence toggle rather than the length-aware fence rules in `plan_grammar.py`. This is outside the migration’s main consumer scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-grammar-compat: Address the concern above.
Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false
