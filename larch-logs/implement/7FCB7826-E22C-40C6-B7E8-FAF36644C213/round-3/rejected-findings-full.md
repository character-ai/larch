### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: [latent] FINAL_SUMMARY_PATH read without DESIGN_TMPDIR constraint
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Parsed `FINAL_SUMMARY_PATH` is used for verbatim file read/emit without proving it lies under `DESIGN_TMPDIR` (`SKILL.md:446,1360`). A same-UID tamperer (or spoofed driver stdout) can set `FINAL_SUMMARY_PATH=/path/to/sensitive/file` in `.design-publish-result.env`; Step 5c item 5 reads and emits that file verbatim to chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: After parse, constrain `FINAL_SUMMARY_PATH` to the canonical tmpdir (realpath prefix check) or always emit `$DESIGN_TMPDIR/final-summary.md` and ignore the parsed path for reads.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: [latent] Post-publish render always uses --outcome approved after publish failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Post-publish render always uses `--outcome approved` even after `PUBLISH_OK=false` (`design-publish.sh:281-285`). Verbatim final-summary emit can show an approved template after publish failure, conflicting with WARN/recovery prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use a failure-aware render outcome or skip approved post-publish render when `PUBLISH_OK=false`.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: [nit] Duplicated stdout rename parse/warn in design-publish.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The stdout parse/warn block at `design-publish.sh:287-302` duplicates `design-init-runparams.sh`. Future rename-contract changes may be applied to one driver only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared rename-output parser into `lib-phase-driver.sh`.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: [nit] Missing intra–Step 5c.5 progress breadcrumb in SKILL
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The intra–5c.5 🔶 breadcrumb was removed; only a status line appears after the full driver returns. Long publish tails show no Step 5c.5 progress until the driver finishes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Document intentional omission or add a single pre-driver 🔶 breadcrumb in SKILL.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: [nit] Third copy of orchestrator result-env parse loop
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `SKILL.md:1327-1353` adds a third copy of the result-env parse loop instead of using `lib-phase-driver` helpers. Allowlist or WARN dedup rules may diverge across Step 0b and 5c over time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate orchestrator parsing via `phase_driver_read_result_env` or a shared SKILL snippet.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

