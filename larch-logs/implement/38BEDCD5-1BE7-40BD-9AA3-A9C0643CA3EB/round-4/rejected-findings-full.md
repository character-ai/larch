### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Residual prompt-injection risk from expanded untrusted issue text is undocumented
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Even with delimiter escaping and untrusted-evidence framing, expanded issue text sent to external LLMs can contain instruction-like content. Reviewers ask to document the residual risk and consider stronger separation if models prove instruction-sensitive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Scope-anchor outbound scrubbing omits broader PII/internal-detail redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Scope-anchor redaction relies on `redact-secrets.sh`, which may not remove internal URLs, account IDs, or operational details from issue bodies before forwarding them to external voters/reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Voter dispatch hard-fails on unreadable scope-anchor file unlike reviewer paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `dispatch-plan-voters.sh` exits when `--scope-anchor-file` is unreadable, while some reviewer prompt paths degrade by omitting missing feature files. This asymmetry can abort a whole review round for transient tmpdir issues unless explicitly intended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Duplicated inline Python and ballot-renumber logic can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `plan-review-loop.sh` contains multiple inline Python blocks duplicating tagged/parity/renumber behavior, including identical ballot-renumber logic. Marker, dedup, aggregation, and ballot behavior can diverge if one copy is changed without the others.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Unused scope-reduction tally helper creates dead API surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-vote-tally.sh` defines `is_scope_reduction_block`, but reviewers report it is not called by production tally paths. This leaves dead or misleading API surface around scope-reduction classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: `check-scope-reduction-marker.sh` duplicates stdin and file-mode Python
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-bash-runtime-output.txt
- **Severity**: nit
- **Concern**: The marker helper has separate duplicated Python blocks for stdin and `--file` modes. Future normalization changes could update only one path and make marker detection inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-bash-runtime-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: MainAgent renderer duplicates redaction/escaping instead of sharing helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The new MainAgent scope-anchor renderer duplicates the redact-and-escape pipeline rather than reusing the shared untrusted-file rendering helper, risking inconsistent prompt escaping across reviewer/voter renderers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

