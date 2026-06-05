### [rejected] FINDING_1

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_1: BODY_HASH docs imply pause marker remains after successful restore
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/design-pause-load.md` still describes marker payload authority without clarifying that the HTML marker block is deleted after a successful body-drift resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Sentinel write failure can leave a partially installed tmpdir
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `cp -R` may populate `DESIGN_TMPDIR` before `.resume-loaded` write fails, leaving partial state that future retries overlay without rollback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Roll back DESIGN_TMPDIR contents on sentinel-write failure, or rename staging dir into place only after sentinel succeeds.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Driver phase-sentinel allowlist is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/design-log-publish.sh` hardcodes the accepted driver phase sentinels separately from `design-driver.sh`, so future driver actions can break pause publishing unless both lists stay aligned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Multiple `WARN=` lines can lose `body-drift` under last-wins parsers
- **Reviewer(s)**: dyn-git-plumbing-output.txt
- **Severity**: latent
- **Concern**: When both `body-drift` and marker-delete failure occur, the loader emits two `WARN=` lines; callers using last-wins parsing can drop the earlier drift warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-plumbing-output.txt: Merge warnings into one comma-separated `WARN=body-drift,marker-delete-failed` value (or emit a single structured warning token) when both conditions apply, and extend the optional harness case to assert both tokens are visible on stdout.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

