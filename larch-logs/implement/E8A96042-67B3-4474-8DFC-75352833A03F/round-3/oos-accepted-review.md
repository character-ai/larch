### FINDING_15: [OUT_OF_SCOPE] Pre-existing session tmpdir sourcing trust
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Pre-existing `plugin-root.env` source and session-env.sh awk in dirty-tree recovery; compromised tmpdir can execute arbitrary shell via sourced env. Out of scope for #3298.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_3: [OUT_OF_SCOPE] Non-2 wrapper exit codes fall through to envelope parse
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Concern**: [latent] Step 0 only handles wrapper exit code 2 explicitly; other non-zero codes can fall through to parse with empty or partial stdout (legacy/pre-existing). Bootstrap or wrapper may return other codes; orchestrator could continue with wrong routing. Optional hardening: exit on `_inv_rc -ne 0` (and `ne 2`) after capturing `_inv_out`.
- **Severity**: latent
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_4: [OUT_OF_SCOPE] Exit-2 handler lacks default STEP_FAILED arm (pre-existing)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Exit-2 handler has no default `STEP_FAILED` arm; unknown failure token yields exit 2 without operator message. Not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


