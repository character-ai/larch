### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Step 3.6 WORSE-majority UX lacks automated coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The operator-facing WORSE-majority path, including AskUserQuestion behavior, `QUALIFICATIONS_SUMMARY`, and Stop cancellation outcome, could regress without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: cap-reached and degraded-empty-collector bypass paths lack structural pins
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The Step 3 short-circuit paths for cap reached and degraded empty collector are not structurally pinned, so future refactors could accidentally route them through Step 3.6 with the wrong loop status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_16: assessor timing-kind structural pins are incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Structural timing-kind tests cover only a subset of the twelve phase-qualified assessor slugs, allowing accidental removal of unpinned slugs to escape CI until runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: write-original structural pin does not verify HARD-only gating
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The `write-original` structural pin does not assert that snapshot creation remains guarded to HARD workflows, so SIMPLE/TRIVIAL paths could start writing snapshots unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: assessor prompt lacks untrusted-input delimiters
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `render-assessor-prompt.sh` inlines the feature and plan files without explicit untrusted-data boundaries, allowing instruction-like text inside revised plans to influence external assessor votes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: assessor dispatch accepts unconstrained input and output paths
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Helper scripts do not confine assessor input/output paths to `DESIGN_TMPDIR`, so direct invocation with arbitrary paths could exfiltrate local files to assessors or write verdicts outside the session tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: write-after refuses overwrite and can preserve stale snapshots
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `snapshot-plan-round.sh` refuses to overwrite an existing `plan-after-round-N`, so same-round replay after `plan.txt` changes can keep a stale snapshot while cursor advancement treats it as valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: degraded verdict artifacts are written non-atomically
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `write_default_verdict_artifacts` can leave a partial `assessor-verdict-round-N.env` if interrupted mid-write.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_28: cancelled-assessor-worse is missing from consolidated cancellation outcomes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `cancelled-assessor-worse` is documented as a state invariant but not listed alongside other cancellation outcomes in a consolidated cancellation-outcomes summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: first-round assessor call always pays for a skipped subprocess
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `assess-plan-round.sh` is invoked on round 1 even though the orchestrator always skips assessment there, adding unnecessary process and parsing overhead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: degraded verdict artifact schema is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `write_default_verdict_artifacts` duplicates degraded `.env` schema logic from `tally-plan-assessor.sh`, making future field additions easy to miss in one path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

