### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Gate-exit-2 checkpoint test does not exercise invalid checkpoint commit range
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-fixture-realism-output.txt
- **Severity**: latent
- **Concern**: The checkpoint gate-exit-2 case exercises accepted-file / ndjson validation rather than an invalid `--commit-range` produced by checkpoint range resolution, so range-resolution failures could regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-fixture-realism-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Missing harness cases for checkpoint CLI / pre-gate exit 2
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The harness lacks explicit checkpoint CLI and pre-gate validation exit-2 cases, such as missing `--implement-tmpdir` or unknown args, leaving usage/validation regressions without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: No explicit origin/main-absent HEAD fallback checkpoint test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The harness does not explicitly test checkpoint behavior when `origin/main` is absent and the helper should fall back to `HEAD`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Best-effort append can lose durable Tool Failures rows
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Failure-path logging uses best-effort append with `|| true`, so disposition-gap exits can stop ship progression while `execution-issues.md` lacks a durable Tool Failures entry if append/redaction fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Checkpoint and gate duplicate non-security OOS counting logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `oos-disposition-checkpoint.sh` and `oos-disposition-gate.sh` both count non-security OOS blocks via the same awk logic, creating redundant work and two update sites if counting rules change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

