### [rejected] FINDING_10

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_10: v1 absent-classification fallback lacks fixture coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The fallback behavior for schema version 1 or absent `design_classification` is not covered, so regressions in the expected HARD default and warning could ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: SIMPLE reviewer prompt can suppress security findings
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: SIMPLE tier emphasis biases reviewers toward EXONERATE without a security carve-out, so auth, secrets, or other security-sensitive design gaps may be dismissed as forward-looking scope creep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: read-design-classification grep fallback can read decoy tier strings
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: On hosts without `python3` or `jq`, the grep fallback in `read-design-classification.sh` can match embedded or malformed JSON substrings instead of the true tier, potentially lowering review strictness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Failed panel retries reuse round artifact paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Because `panel-failed` attempts do not advance the cap counter, repeated retries use the same `--round-num` and `round-N` artifact paths, allowing output overwrite and unclear retry history.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: timing-report duplicates classification parsing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/timing-report.sh` has its own fallback parsing for workflow/tier resolution, including precedence that can drift from `read-design-classification.sh` and mislabel runs on hosts without JSON tooling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

