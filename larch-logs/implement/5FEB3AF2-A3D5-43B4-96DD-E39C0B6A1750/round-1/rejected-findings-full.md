### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Per-job local fix loop clamp lacks path-specific coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: New `normalize_rcc_max_iter` call sites in per-job local verification and fix-loop paths lack harness coverage, so invalid `LARCH_CI_LOCAL_FIX_ITER` values could bypass clamping despite helper-only tests passing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Degraded detection trusts client-reported outputTokens
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The launcher relies on `usage.outputTokens` from the same Cursor JSON envelope as `.result`, so a compromised or buggy client can under-report token usage and bypass degraded-response detection for narration-only output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: First-nonblank-line extraction is duplicated across scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Three production scripts duplicate identical first-nonblank-line `awk` logic, creating risk that future sentinel or whitespace semantics diverge between launcher, collector, and dispatch gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Launcher output classification lacks a single final decision path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Post-`jq` `OUTPUT` handling in `launch-review.sh` uses sequential writers instead of one mutually exclusive decision chain, making it easy for later edits to overwrite degraded-response classification with empty-response classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Dispatch pattern-gate setup is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `dispatch-with-waterfall.sh` repeats `check_file` resolution and readability checks for two pattern flags, increasing maintenance cost for future gates or error-message changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Launcher degraded heuristic thresholds are magic numbers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The `1000` token and `500` byte degraded-response thresholds are inline constants, making them harder to tune, document, and keep aligned with tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Byte/token degraded heuristic can misclassify legitimate short reviews
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The byte/token heuristic can mark legitimately short high-token prose as `CURSOR_DEGRADED_RESPONSE`, while threshold edge cases may still allow compact narration-only outputs to remain `STATUS=OK` on ungated paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

