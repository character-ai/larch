### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Plan validator unconditional behavior lacks harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no harness directly invoking `invoke-plan-validator.sh` for SIMPLE and HARD fixtures, so quick-mode skip behavior could reappear in the helper without test coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Plan review prompt allows control-character path injection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `render-plan-review-prompt.sh` embeds the plan file path in external reviewer prompts without rejecting newline or control-character paths, allowing a malicious path to split the prompt and inject instruction-like lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Classification grep fallback can misclassify malformed run params
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `read-design-classification.sh` falls back to matching `SIMPLE` or `HARD` substrings in raw file bytes. Malformed run-params containing decoy strings could select the wrong tier and alter caps or reviewer emphasis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Empty review-round counter is treated as zero
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: An empty `review-round-count.txt` is treated as `0` without warning, allowing extra review rounds without audit visibility if the counter file is truncated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Plan review loop cap ownership docs are misleading
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/plan-review-loop.md` says Gate C owns cap enforcement, which may lead implementers to put counter logic in `plan-review-loop.sh` instead of keeping Step 3 responsible for skipping and Gate C responsible for omitting Re-run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

