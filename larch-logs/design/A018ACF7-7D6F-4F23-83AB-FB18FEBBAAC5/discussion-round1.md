## Decision 1: Scope of structural test
- **Question**: Should the test only assert current state, backfill the canonical phrase into missing locations, or fail-now?
- **Resolution**: Add canonical phrase verbatim to the 3 missing locations (plan-review.md Voter 1 prompt, plan-review.md shared Voter 2/3 prompt, render-voter-prompt.sh — which is the actual renderer called by dispatch-plan-voters.sh make_prompt_file()) and add the structural grep check that asserts the phrase across all 4 locations.
- **Source**: user

## Decision 2: Test home
- **Question**: New harness or extend existing test-design-structure.sh?
- **Resolution**: Extend scripts/test-design-structure.sh with a new numbered check.
- **Source**: user
