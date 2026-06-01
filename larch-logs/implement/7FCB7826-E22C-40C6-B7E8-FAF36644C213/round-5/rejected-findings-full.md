### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Destructive gates rely on mutable result-env KVs without integrity checks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Parsed `PLAN_WRITE_OK`/`PUBLISH_OK` gate sentinel cleanup and rename without integrity beyond symlink check. Tampered `PUBLISH_OK=true` after failed publish could skip tmpdir preservation and run `[DESIGNED]` rename without logs on the default branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Gate destructive actions on re-checkable artifacts or document same-UID trust boundary; do not rely solely on mutable result env.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Duplicate KV/stdout parse helpers between design-publish and design-init-runparams
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `parse_kv_from_output` and RENAMED stdout parsing in `design-publish.sh` duplicate logic in `design-init-runparams.sh`. A future key or rename contract change may update one driver only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared parse helpers into lib-phase-driver.sh in a follow-up.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Structure tests lack design-publish setup-order pins
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-design-structure.sh` partially mirrors design-publish setup-order checks vs `design-init-runparams`. Regressions in `set -u` or wrong plugin-root resolution may not be caught by structure pins.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add greps for canonical DESIGN_TMPDIR before SESSION_ENV_PATH and phase_driver_resolve_plugin_root.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Whitespace-only `--session-id` rejection untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Whitespace-only `--session-id` rejection is untested in `test-design-publish.sh`. Validator drift could allow whitespace `SESSION_ID` and change publish/rename branches silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add argv case expecting exit 2 for whitespace-only session-id.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Parsed `FINAL_SUMMARY_PATH` lacks under-`DESIGN_TMPDIR` validation before verbatim emit
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Parsed `FINAL_SUMMARY_PATH` drives verbatim file emit without under-`DESIGN_TMPDIR` validation. A same-UID tmpdir writer could overwrite `.design-publish-result.env` with `FINAL_SUMMARY_PATH` pointing at another readable file; the orchestrator would emit that file into top chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: For emit always use $DESIGN_TMPDIR/final-summary.md or canonicalize and require resolved path prefix == $DESIGN_TMPDIR/.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

