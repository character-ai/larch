### [rejected] FINDING_1

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_1: write-design-current-env misses repo binding
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Resume and 5.5-bis refresh `write-design-current-env.sh` without `--repo`, so cross-repo resume can lose the bound repo and pause/prelude operations may target the wrong GitHub issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: recovery-only publish reports pause success too quietly
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: When publish falls back to `RECOVERY_BRANCH`, `design-pause-save.sh` can still emit `PAUSE_OK=true` without a stdout warning, so operators may believe the default branch contains the latest snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: pause/resume test stub lacks manifest
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The offline publish stub in `test-design-pause-resume.sh` omits `manifest.json`, but `design-pause-load.sh` requires it, leaving the pause/resume harness red with `missing-restored-artifact`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: recovery branch validation is not tied to RUN_ID
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `LOG_RECOVERY_BRANCH` accepts any `larch-log-design-*` ref instead of requiring a branch derived from the validated `RUN_ID`, allowing attacker-controlled restored artifacts under a victim run id if an editor can modify the issue and push a branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: issue number is persisted too late for pause
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `ISSUE_NUMBER` is not written to session env until later substeps, so invoking `/larch:pause` after issue fetch but before rename can exit with nothing to pause while `/design` is mid-run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: manifest validation assumes jq exists
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `design-pause-load.sh` validates `manifest.json` with `jq` but does not guard for missing `jq`, producing a shell failure instead of structured `LOAD_OK=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_2: defensive pause prelude misses repo binding
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The Bash prelude invokes `design-pause-save.sh` without passing the pause-time `REPO`, so defensive `.pause-requested` saves can resolve the wrong repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: duplicated marker parsing logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `design-pause-save.sh` and `design-pause-load.sh` duplicate awk logic for stripping/parsing `larch:design-pause` markers, risking inconsistent behavior if marker grammar changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_4: restored artifacts installed before marker delete failure handling
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `design-pause-load.sh` installs restored artifacts into `DESIGN_TMPDIR` before deleting the pause marker. If marker deletion fails, Step 0b may continue as a fresh run with a polluted tmpdir while the marker remains, creating hybrid retry state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: pause-state redaction runs twice
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `design-pause-save.sh` redacts pause-state twice on the recovery-branch path, adding minor redundant I/O.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_9: pause sentinel has no shipped producer
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The defensive `.pause-requested` prelude is present, but shipped `/larch:pause` does not arm that sentinel, so mid-Bash deferral and `/loop` pause scenarios do not actually trigger outside tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

