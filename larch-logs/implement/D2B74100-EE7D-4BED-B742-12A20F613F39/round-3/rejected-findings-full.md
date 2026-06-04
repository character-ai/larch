### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Duplicate publish-recovery metadata validators can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Publish-recovery metadata validation is duplicated between `design-publish.sh` and `render-final-summary.sh`, creating drift risk between summary rendering and warning behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Pause state is written before publish succeeds
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `pause-state.txt` can be written before publish succeeds, leaving local state that implies resumability even when no marker or recovery metadata was published.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Step 5c can be marked complete on empty `SESSION_ID`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `step-5c` is written for `publish-skipped` when `SESSION_ID` is empty, so resume may not retry the publish tail after transient session-id loss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Publish-skipped uses success-class footer and cleanup path
- **Reviewer(s)**: dyn-publish-lifecycle-output.txt
- **Severity**: latent
- **Concern**: Empty `SESSION_ID` produces an honest `publish-skipped` summary but still uses success footer/cleanup behavior, weakening terminal signals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-lifecycle-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Source-env parsing helpers remain duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `source_env_get` is not shared with other awk-only source-env readers, leaving multiple parsers for the same contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Pause-save contradictory envelope clears recovery branch
- **Reviewer(s)**: dyn-pause-recovery-output.txt
- **Severity**: latent
- **Concern**: In `design-pause-save.sh`, non-zero publish rc plus stdout `PUBLISH_OK=true` forces failure but blanks `RECOVERY_BRANCH`, preventing the usual recovery-branch-only resumable marker path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-recovery-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Harness assertion id collides with Step 5c numbering
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Assertion id `(27)` in `test-design-structure.sh` collides semantically with Step 5c `(27)` pins, making CI failures ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Publish-skipped result env omits explicit `PUBLISH_OK`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Empty-`SESSION_ID` publish-skipped runs omit `PUBLISH_OK` from `.design-publish-result.env`, so env-only consumers may confuse skip with failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

