### [rejected] FINDING_11

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_11: Empty-porcelain pause publish can skip changed local state
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/design-log-publish.sh` can return `PUBLISH_OK=true` on empty porcelain without committing local tmpdir changes. A second pause after resume may record a step from local sentinels while restoring an older default-branch snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_12: Recovery branch rejected after push failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Push failure recovery uses or requires a recovery ref such as `larch-log-design-recovery-RUN_ID`, but `design-pause-save.sh` rejects it or writes no marker. A recoverable local snapshot can therefore produce `PAUSE_OK=false` with no cross-session resume path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Synchronous pause can race defensive prelude save
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `/larch:pause` arms `.pause-requested` and then runs synchronous save, while the `/design` prelude may also exec save. Concurrent saves can race on the issue body and log branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Duplicate Step 1c completion sentinel guidance
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` contains duplicate Step 1c completion-sentinel instructions, creating drift risk for future edits and confusing orchestrators or structure checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Duplicate pause-state redaction pass
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/design-pause-save.sh` runs duplicate secret-redaction passes over unchanged pause-state content, adding subprocess cost and duplicated failure handling on every pause save.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Marker parse and classify logic is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Marker parse/classify logic is implemented separately in `scripts/design-pause-save.sh`, `scripts/design-pause-load.sh`, and `scripts/named-block-write.sh`, so malformed-marker behavior and grammar changes require coordinated edits across multiple scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

