### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Assessor reasoning can inject or bloat verdict/env output
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: External `QUALIFICATIONS` and `REASONING` text is written into `.env` and verdict artifacts without newline/control-character sanitization or length limits. Malicious output can inject misleading KV-like lines or operator-facing rationale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Assessor output paths from quiet log are not confined to DESIGN_TMPDIR
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `assess-plan-round.sh` trusts output path KVs parsed from the quiet log, allowing a tampered log to point tally at arbitrary local files instead of constructed files under `DESIGN_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Assessor prompts can expose secrets to external tools
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `render-assessor-prompt.sh` includes full plan and feature text for Codex/Cursor without redaction or explicit security documentation. Secrets pasted into design artifacts can be sent to third-party APIs and retained in session bundles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Missing-snapshot fail-open can bypass the WORSE gate under session-dir tampering
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: If the threat model includes mutation of files under `DESIGN_TMPDIR`, missing-snapshot and degraded paths can force NOT_WORSE/skipped behavior and avoid operator acknowledgement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: tally-plan-assessor does not validate tmpdir or output path roots
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Direct invocation or future callers can pass `--*-output` paths outside the session dir because `tally-plan-assessor.sh` does not validate `DESIGN_TMPDIR` or confine inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: write-after snapshot preservation can leave stale after-round inputs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `snapshot-plan-round.sh write-after` is write-once. Re-entering the same round after `plan.txt` changes can leave `plan-after-round-N.txt` stale, so assessor comparisons use the wrong baseline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Some short-circuit statuses skip Step 3.6 and may leave ambiguous baselines
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `cap-reached` and degraded-empty-collector paths skip Step 3.6. Later Gate C re-entry may interact with old after-round files unless cursor advancement explicitly accounts for whether Step 3.6 completed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Write-after failure policy is inconsistent with missing-snapshot fail-open behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `write-after` failure currently exits 1 and aborts `/design`, while missing snapshots inside `assess-plan-round.sh` warn and fail open. The implementation and docs need a single policy: either fail open and skip assessment, or document and enforce a hard stop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: KV parsing is duplicated and lacks a canonical helper or contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Step 3, Step 3.6, and `assess-plan-round.sh` each parse KV output independently. Future contract changes require coordinated edits in multiple places.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Cancelled assessor summary title patch is brittle
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `patch_assessor_worse_title` assumes the title is line 1. A renderer layout change could break cancelled-assessor-worse titles without obvious failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

