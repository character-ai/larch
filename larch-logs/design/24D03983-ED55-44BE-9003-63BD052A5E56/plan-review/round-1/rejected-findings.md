### [Plan Review] FINDING_6

### FINDING_6: Bash opt-in is not documented as recovery for Python-path regressions
- **Reviewer(s)**: Codex-dyn-rollout-contract
- **Severity**: important
- **Concern**: The planned docs and acceptance checks advertise bash as an opt-in path but not as a recovery mechanism for Python-path regressions, despite open soak blockers. Operators who hit a failed Python Step 8+ run may not know to rerun with `LARCH_SHIP_PR_IMPL=bash`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-rollout-contract: Add a single recovery sentence to the planned config doc edit: if Step 8+ regresses on the python path, rerun with LARCH_SHIP_PR_IMPL=bash; include that guidance in the manual acceptance check.

