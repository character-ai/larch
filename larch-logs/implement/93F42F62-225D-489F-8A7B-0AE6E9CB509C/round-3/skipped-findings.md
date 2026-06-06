### FINDING_7: design-route changes are outside the declared plan file set
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-contract-drift-output.txt
- **Severity**: latent
- **Concern**: `design-route.sh` / `design-route.md` were changed to relay `MARKER_CLEARED`, but those files were not listed in the plan’s file set, expanding the route-driver contract without plan amendment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add design-route files to the plan amendment or revert route changes if MARKER_CLEARED relay is not needed downstream.
  - From dyn-contract-drift-output.txt: Either fold `design-route.sh` / `design-route.md` into the plan acceptance criteria explicitly, or narrow the route diff to passthrough-only behavior already covered by loader `WARN=` lines until SKILL.md is updated.



