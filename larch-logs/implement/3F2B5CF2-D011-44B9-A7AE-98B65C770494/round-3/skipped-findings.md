### FINDING_11: Candidate Patch Filename Documentation Is Stale
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Documentation still refers to `tier-candidate.patch`, while the code writes `codex-output-candidate.patch`/`*-output-candidate.patch`. Operator-facing docs and fixtures can become confusing even if allowlists still match.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.



