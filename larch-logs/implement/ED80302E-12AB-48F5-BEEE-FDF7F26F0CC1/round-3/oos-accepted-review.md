### FINDING_15: [OUT_OF_SCOPE] ship-pr redactor failure relays raw tool output
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/ship-pr.sh` can relay raw tool output through `larch_err` when `redact-secrets.sh` fails, potentially exposing tokens or tmpdir paths; reviewer marked this pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_16: [OUT_OF_SCOPE] create-pr surfaces raw gh stderr
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/create-pr.sh` surfaces raw `gh` stderr through `larch_err`, potentially exposing auth or host details; reviewer marked this pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


