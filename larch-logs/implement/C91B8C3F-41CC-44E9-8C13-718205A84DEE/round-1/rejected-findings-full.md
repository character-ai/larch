### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Nonconforming marker precedence is undocumented
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: When output contains both attestation and nonconforming pseudo-finding markers, validation still exhausts but reports `nonconforming_heading_with_attestation` rather than `preamble_finding_substring`. If intentional, the precedence should be documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Attestation-only success can wipe a nonempty ballot
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A static empty-merge attestation token can cause validation to succeed and replace a nonempty pre-merge ballot with whitespace-only `findings.md`, allowing review to proceed with zero in-scope findings. The behavior is documented, but reviewers recommend operator-visible signaling or secondary checks for `INPUT_COUNT>0` and `MERGED_COUNT=0` if stronger integrity is needed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_9: Zero-block success must keep whitespace-only persistence guard
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Zero-block success intentionally persists whitespace-only `findings.md`, preventing accepted narrative text from leaking into voter prompts or ballot artifacts. Reviewer indicates no change is needed beyond retaining the guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

