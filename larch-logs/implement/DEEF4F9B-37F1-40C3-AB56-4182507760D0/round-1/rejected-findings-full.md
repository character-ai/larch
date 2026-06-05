### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Step 3b FINALIZE ordering is not pinned inside the fence
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The Step 3b boundary structure check verifies substring presence but not that FINALIZE completes before `.completed/step-3b` is written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: No executable test covers Step 3b FINALIZE on empty review state
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Driver behavior at the new Step 3b FINALIZE call site is prose-pinned but not exercised with an empty review-state tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Gate-B bypass routes omit the Step 3b completion boundary
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Gate-B-bypass branch bullets route to Step 3b without naming the completion boundary, risking skipped FINALIZE before Step 4 artifact reads on panel-failed/tally-error paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Legacy SIMPLE compatibility guard does not verify or restore sentinel artifacts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-resume-legacy-output.txt
- **Severity**: latent
- **Concern**: The Step 2a.5 compatibility guard backfills only `.completed/step-2a.5`; legacy or corrupted SIMPLE resumes with missing sentinel artifacts can proceed to Step 2b with incomplete sketch state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-resume-legacy-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Missing pause/resume fixture for finalize-present but step-3b-absent state
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: There is no fixture for `.completed/finalize` present while `.completed/step-3b` is absent, so regressions in resume-at-3b boundary rerun behavior could go unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Step 2a.5 compatibility guard ignores SIMPLE pause metadata when classification defaults HARD
- **Reviewer(s)**: dyn-resume-legacy-output.txt
- **Severity**: latent
- **Concern**: The guard repairs `.completed/step-2a.5` only when `read-design-classification.sh` returns `SIMPLE`; legacy snapshots with SIMPLE pause metadata but missing/invalid classification can default to HARD and skip repair.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-legacy-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Duplicate FINALIZE fences may drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Step 3b boundary and Step 4 compatibility guard duplicate FINALIZE bash blocks, creating a maintenance risk if future failure-handling edits update only one copy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_25: Step 2a entry fence may leak `errexit` into later bash fences
- **Reviewer(s)**: dyn-bash-fences-output.txt
- **Severity**: latent
- **Concern**: `set -e` is enabled inside the SIMPLE branch but not reset, so a reused shell session could inherit `errexit` and unexpectedly abort later unrelated commands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-fences-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Routing guard exemption is too broad
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-design-structure.sh` exempts any line mentioning the Step 3b completion boundary, even if that line does not require the actual FINALIZE fence, allowing prose-only mentions to satisfy CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_9: Harness ordering failure message is inverted
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: A guard-line ordering assertion in `scripts/test-design-structure.sh` reports the wrong ordering expectation, which would misdirect debugging when CI fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

