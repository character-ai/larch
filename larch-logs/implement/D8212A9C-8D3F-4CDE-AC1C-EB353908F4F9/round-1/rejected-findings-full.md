### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: `rc=2` from `run-step3-review.sh` aborts full `/design`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `rc=2` (e.g. invalid `LARCH_DESIGN_ROUND_CAP`) now maps to `exit 1` and aborts the entire `/design` session instead of a panel-failed short-circuit to Step 3b. UX may be harsher than intended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Confirm intended UX or map exit 2 to a documented terminal outcome.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: `RUN_STEP3_EMIT_PREVIEW_SH` override without path validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `RUN_STEP3_EMIT_PREVIEW_SH` is invoked without path validation or a production opt-in gate. A stale or attacker-influenced shell export could run arbitrary code with design-session privileges during `/design` `--preview-only`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document as harness-only in SECURITY.md; optionally require an explicit opt-in env flag and/or restrict overrides to paths under PLUGIN_ROOT.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Integration harness omits explicit `--no-preview`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-design-multi-round-integration.sh` omits explicit `--no-preview` on the `run-step3-review.sh` call; default-mode changes would not be signaled by the test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Pass --no-preview on the run-step3-review.sh integration call.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Step 3 fence WARN replay lacks dedup vs Step 0b/postplan
- **Reviewer(s)**: dyn-display-parse-sync-output.txt
- **Severity**: latent
- **Concern**: WARN handling replays from both safe result-env read and stdout parse with no dedup, unlike Step 0b route/publish and `design-postplan-emit.md`. Today the driver does not persist `WARN=` to `.step3-review-result.env`, but double-emit is latent if WARN appears in file and stdout (symlink-fallback / partial-write).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-display-parse-sync-output.txt: Mirror postplan/Step 0b: collect WARN bodies in an array during file parse, then replay stdout `WARN=` only when that body was not already emitted; extend `test-step3-orchestrator-fence.sh` with a file+stdout duplicate WARN case expecting a single chat line.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Twelve-key allowlist duplicated across SKILL and harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The twelve-key allowlist is duplicated across display pass, file parse, and stdout parse in `SKILL.md` and mirrored in `test-step3-orchestrator-fence.sh`. Adding a 13th driver KV requires many manual edits; one site will be missed and precedence/display will drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Centralize allowlist documentation and grep pins, or extract a shared key list for harness-only use in a follow-up.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Preview sentinel uses `-e` instead of `-f`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Sentinel re-entry check uses `-e` not `-f`. `.step3-entry-plan-printed` created as a directory would suppress preview forever without a valid preview file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use [[ -f ... ]] for re-entry suppression.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Thin fence file-first precedence when driver fails to refresh env
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: On `rc!=0`, an existing safe `.step3-review-result.env` is treated as authoritative and stdout does not override `LOOP_STATUS`/`TALLY` even when the driver failed to refresh the file. A prior run can leave `LOOP_STATUS=complete`; the current run prints `LOOP_STATUS=panel-failed` on stdout but `phase_driver_write_result_env` fails, so the orchestrator may enter Gate B instead of the panel-failed short-circuit to Step 3b.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document as residual risk or narrow file-first rule when write failed (WARN/refusal) or file is older than this invocation.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Symlinked `.step3-review-result.env` skipped without breadcrumb
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Symlinked `.step3-review-result.env` is skipped silently with no operator breadcrumb; operators may see stdout override with no explanation when a stale symlinked env exists beside a safe file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Emit one info line on -L skip or document in Step 3 prose.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

