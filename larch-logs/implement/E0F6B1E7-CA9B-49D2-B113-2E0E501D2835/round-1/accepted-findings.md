### FINDING_1: Gate A See-full-plan contract lacks structural pins
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Gate A rename and See-full-plan drop-on-re-fire behavior is not pinned by `scripts/test-design-structure.sh`, so future Gate-A-only drift could pass while Gate C pins still succeed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: Gate C missing-plan pick path is underspecified
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Gate C does not define pick-time handling when `plan.txt` is missing or empty after the presentation warning-only path, so selecting See full plan can show nothing and then reduce the menu without an explicit recovery path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


