### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Repeated parser subprocesses slow tally runs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `tally-plan-review.sh` repeatedly invokes `parse-judge-vote-and-rating.sh` per finding/voter with no cache, multiplying subprocess cost on large ballots and repeated CI harness runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Classification output path can overwrite outside DESIGN_TMPDIR
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--findings-classification-out` lacks containment and symlink checks, allowing a caller-supplied absolute path or destination symlink to truncate or overwrite files outside the design session directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Voter file paths can read arbitrary host files
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--voter SLOT:PATH` accepts any readable non-symlink file, so a misconfigured tally can ingest arbitrary host-file lines and publish derived forensic rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Missing ballot ID lines are reported as uncertain
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When no anchored ballot ID line exists, the parser emits `PARSED_UNCERTAIN=true`, conflating absent vote lines with explicit or inferred judge uncertainty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Hyphen-glued vote/rating tokens drop rating axes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Axis parsing only recognizes whitespace-separated tokens after the vote, so lines like `YES-CORRECTNESS=...` record the vote but drop rating axes and infer uncertainty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: Dispatcher traceability points at the wrong prompt file
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The plan listed `dispatch-plan-voters.sh` for prompt extension even though prompt text lives in `render-voter-prompt.sh`, making traceability look incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Vote tally helpers are duplicated and drifting
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `count_votes_for_id` duplicates newer parser-based counting logic, leaving maintainers with multiple vote-counting paths that may diverge between plan review, code review, and documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Axis enum definitions are duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Axis enums are duplicated between the parser and voter prompt rendering, so renaming an axis in one place can silently break prompt/parser compatibility.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: Parser records ratings even when the vote token is invalid
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Malformed anchored vote lines can produce empty vote cells but populated rating-axis cells, making TSV rows look partially valid while tally counts the judge as errored.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

