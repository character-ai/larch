### FINDING_12: [OUT_OF_SCOPE] `EVIDENCE_TOKEN` regex is duplicated instead of derived
- **Reviewer(s)**: cursor-specialist-plan-fidelity-auto
- **Severity**: nit
- **Concern**: The writer uses a shared evidence-token label constant, but the parser hardcodes the token name again. A future label rename could desynchronize the write and read paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-auto: Build the regex from EVIDENCE_TOKEN_LABEL or one shared `Final` used by both paths.

