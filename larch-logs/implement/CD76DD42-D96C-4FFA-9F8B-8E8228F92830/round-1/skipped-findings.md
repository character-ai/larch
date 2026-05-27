### FINDING_3: Sourced re-entry guard library is missing from dead-script excludes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/lib-design-reentry-guard.sh` is sourced-only but is not excluded in `agent-lint.toml`, so `make lint` / pre-commit can flag it as dead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add lib to agent-lint.toml exclude with comment mirroring lib-title-eligibility.
  - From cursor-specialist-testing-output.txt: Add scripts/lib-design-reentry-guard.sh (and .md if needed) to agent-lint.toml exclude alongside lib-title-eligibility.sh.
  - From cursor-specialist-plan-fidelity-output.txt: Add scripts/lib-design-reentry-guard.sh to exclude with sourced-only comment mirroring lib-title-eligibility.sh.



