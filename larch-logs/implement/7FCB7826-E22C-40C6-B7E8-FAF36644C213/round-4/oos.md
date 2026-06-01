### FINDING_14: [OUT_OF_SCOPE] docs/linting.md — missing `make test-design-publish` table row
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Missing `make test-design-publish` table row in `docs/linting.md`. Contributors may not discover the harness target. Add a `linting.md` row mirroring `test-design-driver`.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] test-design-multi-round-integration.sh — no E2E Step 5c driver integration
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No E2E Step 5c driver integration in the diff. Runtime orchestrator parse/emit bugs are possible despite the unit harness. Pre-existing; add an integration case only if policy requires E2E for phase drivers.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] branch commits — upgrade-larch #3320 bundled with design-publish PR
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `upgrade-larch` #3320 changes are bundled on the same branch vs `main`. Unrelated scope is mixed into the design-publish PR; not a plan miss for Step 5c itself. Treat as a separate feature when reviewing plan fidelity for design-publish only.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_23: [OUT_OF_SCOPE] SKILL.md — `PUBLISH_OK` gate on step-5c appears review-driven vs plan-authored
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The `PUBLISH_OK` gate on step-5c looks review-driven, not plan-authored. The structure harness now encodes behavior the plan explicitly rejected. Reconcile with the plan or amend plan/acceptance if the tighter gate is desired.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] test-design-structure.sh — structure pins omit design-publish exit 3
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Structure pins cover design-publish exit 2 and exit 1 contracts but not exit 3. Exit 3 handling in `SKILL.md` could regress without CI signal. Add grep pins for publish-tail incomplete (exit 3) abort prose alongside existing exit 2/1 pins.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

