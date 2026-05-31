### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: `plan_block_present` duplicates `plan-block-read.sh` pairing logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `plan_block_present()` in `skills/design/scripts/design-route.sh` (38–58) reimplements marker pairing logic from `scripts/plan-block-read.sh`. If `plan-block-read.sh` gains new malformed-body handling, `design-route.sh` may route `already-planned` / `proceed` differently on edge-case bodies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared helper or call `plan-block-read` in a presence-only mode.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: No offline harness for full `design-route.sh` routing matrix
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No offline harness executes the routing matrix per plan Decision 2. Routing-order or plan-detection regressions can ship until manual `/design` smoke.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add minimal stub-harness or document mandatory smoke matrix in PR test plan.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Unquoted `$_value` in WARN/ERROR dedup uses pathname expansion
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Unquoted `$_value` in WARN/ERROR dedup `[[ ]]` at `SKILL.md` 250–262 uses pathname expansion; glob characters in pause-load tokens can suppress or corrupt breadcrumbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Quote values; use exact-match dedup instead of glob substring test.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Cached `issue-body.txt` vs `gh` re-fetch in pause-load can diverge
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Cached `issue-body.txt` vs `gh` re-fetch inside `design-pause-load` (`design-route.sh` 196–232) can disagree after mid-run issue edits, causing resume vs already-planned mismatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Thread body file into pause-load or single-source body reads.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: `validate_plain_scalar` / `validate_repo` duplicated across Step 0b drivers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `validate_plain_scalar` / `validate_repo` are duplicated in `design-route.sh` (23–36) and `design-init-runparams.sh` (20–41). Future argv validation changes require two edits and can drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Move validators into `lib-phase-driver.sh` and source from both drivers.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: Init handoff prints duplicate `WARN` without route-style deduplication
- **Reviewer(s)**: dyn-kv-protocol-output.txt
- **Severity**: latent
- **Concern**: Post-gate init handoff (`SKILL.md` 378–388) prints `WARN` on every file-first and stdout hit without deduplication, while route handoff dedupes then prints once (247–270). Same `WARN` from result env and `_init_out` (e.g. rename failure) can duplicate breadcrumbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-protocol-output.txt: Reuse the route pattern (accumulate `WARN` lines, print once after merge) or gate stdout `WARN` printing when the value was already consumed from the file.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

