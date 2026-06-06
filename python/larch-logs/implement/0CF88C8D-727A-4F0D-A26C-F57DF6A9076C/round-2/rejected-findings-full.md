### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: End-to-end accepted-OOS filing path lacks parse-input batch coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests stop at gate/counter behavior and do not verify that normalized legacy-derived OOS blocks parse through `/issue` batch filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Reader gate lacks a bare FINDING_ pass-through regression
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No harness documents that bare `FINDING_` blocks without disposition should be ignored by the reader/gate, so future reader changes could miscount mixed files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Python legacy-header regex accepts trailing tags beyond the stated plan form
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Python legacy-header matching accepts trailing `[OUT_OF_SCOPE]` tags via `.*`, while the plan’s regex was narrower. The behavior may be intentional parity with AWK, but docs/plan need alignment or the regex should be tightened.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: tally-code-votes uses command substitution for multi-line normalized OOS blocks
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: nit
- **Concern**: Capturing normalized accepted OOS via shell command substitution loads whole blocks into shell memory and strips trailing newlines, unlike the streaming append pattern used elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: oos-serialize duplicates canonical OOS header normalization instead of using the shared helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-artifact-contracts-output.txt
- **Severity**: important
- **Concern**: `oos-serialize.sh` performs its own inline header rewrite instead of delegating to `normalize-oos-block-header.sh`, despite docs describing the helper as the shared normalization authority. That creates another normalization surface likely to drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-artifact-contracts-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

