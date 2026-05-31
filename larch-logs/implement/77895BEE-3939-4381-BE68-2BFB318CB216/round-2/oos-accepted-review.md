### FINDING_12: [OUT_OF_SCOPE] --skill label unvalidated in degraded-tools-gate.sh explanation text
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: --skill label is unvalidated in explanation text. Pre-existing presentation-only risk if orchestrator passes unexpected --skill value.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate against allowlist design|implement|review|research or default to this.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated


### FINDING_13: [OUT_OF_SCOPE] --caller-env can skip probes and hide both-tools-down before gate
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: --caller-env can skip probes and set presence from caller file. Pre-existing; can hide both tools down before gate runs. Out of scope for this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document or harden separately.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated


