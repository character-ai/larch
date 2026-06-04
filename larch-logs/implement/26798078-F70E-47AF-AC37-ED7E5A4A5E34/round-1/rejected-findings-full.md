### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Validator stdout and stderr are merged before KV parsing
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-shell-flow-output.txt
- **Severity**: latent
- **Concern**: `design-publish.sh` captures validator stderr into the same stream as stdout and parses last-wins `VALIDATE_STATUS`, so diagnostic or spoofed stderr KVs could theoretically override the real status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-shell-flow-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Auto-repair may silently alter security-sensitive plan content
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The auto-repair flow can edit plan artifacts without operator prompt, potentially changing security-sensitive content before re-validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Publish pause path lacks result-env/status handoff
- **Reviewer(s)**: dyn-contract-drift-output.txt
- **Severity**: important
- **Concern**: `design-publish.sh` `exec`s `design-pause-save.sh` on pre-side-effect pause without first writing `.design-publish-result.env` or stdout KVs, so the orchestrator may treat a valid pause as missing result state and abort.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-drift-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Publish driver only checks pause once before combined side-effect tail
- **Reviewer(s)**: dyn-pause-publish-output.txt
- **Severity**: important
- **Concern**: Folding validation, redaction, plan write, publish, rename, and marker creation into one `design-publish.sh` process leaves no pause checkpoints before later side effects, despite docs implying finer-grained protection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-publish-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: --skip-validate can publish command-unsafe plans after operator accept
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--skip-validate` bypasses composed-plan command validation while still allowing `larch:plan` publication, so malicious or defective commands may reach downstream `/implement`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

