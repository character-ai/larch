### FINDING_1: Structural harness rejects SIMPLE sketch budget
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` still forbids `sketch_budget=0`, but `skills/design/SKILL.md` now intentionally requires that value for the SIMPLE tier. This makes `make test-design-structure` / `relevant-checks` fail on the current branch and blocks the tier change from merging cleanly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Missing pins for contract-drift abort and removed HARD fallback
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The structural harness does not pin the new Step 0b contract-drift abort behavior or assert absence of the old silent HARD fallback prose. A future SKILL revert could restore defaulting to HARD without failing `make test-design-structure`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Bash authoring docs did not implement planned subsection
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `BASH_AUTHORING.md` only adds a short inline paragraph where the plan called for a dedicated §3 subsection with a `%%` / `##` code example and a `make lint-renderer-substitution-safety` cross-reference. Operators may miss the canonical split pattern and enforcement target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

