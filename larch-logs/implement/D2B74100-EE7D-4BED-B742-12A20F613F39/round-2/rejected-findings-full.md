### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Duplicate validate_repo implementations can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `validate_repo` is duplicated across multiple scripts. Future grammar or security-rule changes could be applied to only some copies, causing inconsistent repo acceptance across publish, pause, and post-plan paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Failed-publish step-5c withholding lacks executable pause/resume coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The contract that failed publish should not write `.completed/step-5c` is only structurally pinned, not covered by an executable pause/resume harness. A regression could advance resume past Step 5c and prevent retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: design-postplan-emit builds --repo exec arguments defensively weakly
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/design-postplan-emit.sh` uses unquoted parameter expansion for `--repo`. Current validation mitigates this, but an argv array or explicit conditional exec would be safer if validation is ever bypassed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: design-pause-load does not validate caller-supplied --repo
- **Reviewer(s)**: dyn-repo-routing-output.txt
- **Severity**: latent
- **Concern**: `scripts/design-pause-load.sh` validates marker/restored repo values but not argv `--repo` before building `gh` arguments. Direct or future callers that bypass `design-route.sh` validation can pass malformed repo values to `gh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-repo-routing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: render-run-summary documentation is split on publish-skipped
- **Reviewer(s)**: dyn-summary-contracts-output.txt
- **Severity**: latent
- **Concern**: `scripts/render-run-summary.md` lists `publish-skipped` in a later normative table but omits it from primary Usage/Output sections, creating a contract mismatch for downstream docs or tooling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-contracts-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: postplan pause aborts on invalid persisted REPO instead of returning pause-save envelope
- **Reviewer(s)**: dyn-pause-recovery-output.txt
- **Severity**: important
- **Concern**: `_postplan_pause_checkpoint` validates repo before writing `POSTPLAN_EMIT_STATUS=paused` and before execing `design-pause-save.sh`. A malformed persisted repo exits as a postplan configuration error instead of delegating to pause-save’s structured `PAUSE_OK=false` / `ERROR=invalid-repo` response.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-recovery-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: pause-save logs only stderr for contradictory publish envelopes
- **Reviewer(s)**: dyn-pause-recovery-output.txt
- **Severity**: nit
- **Concern**: When pause-save normalizes non-zero publish output that claimed `PUBLISH_OK=true`, it logs only stderr. If the misleading envelope was on stdout and stderr was empty, diagnostics omit the evidence that caused normalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-recovery-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_30: pause-save can write unsanitized publish metadata into pause-state
- **Reviewer(s)**: dyn-shell-parsing-output.txt
- **Severity**: important
- **Concern**: `scripts/design-pause-save.sh` parses publish stdout with simple `awk -F=` and writes `RECOVERY_BRANCH` into `pause-state.txt` without newline/CR or branch-slug validation, allowing corrupted or hostile publish output to inject extra state lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parsing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Clarify publish fail-closed handling is prompt-orchestrated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Clarify-only publish handling relies on prompt-side orchestration rather than the scripted `design-publish.sh` normalizer. Future orchestrator drift could again trust contradictory `PUBLISH_OK=true` output from a non-zero publish exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: publish-skipped note text is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `render-final-summary.sh` duplicates the publish-skipped note in primary and fallback render paths, creating a small maintenance/desync risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: publish-skipped step-5c sentinel behavior is ambiguous
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 5c may be marked complete when publish is skipped because `SESSION_ID` is empty, causing resume to skip the publish tail. The contract should clarify whether skipped publish is intentionally terminal or whether retry should be possible.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

