### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: LARCH_*_SH env overrides allow arbitrary child scripts
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_SNAPSHOT_PLAN_ROUND_SH` and `LARCH_ASSESS_PLAN_ROUND_SH` substitute child script paths from environment. Attacker-controlled env in shared CI runs could execute arbitrary scripts as Step 3.6 children under the runner UID.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Restrict overrides to harness mode or document and unset in production orchestration entrypoints.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: write-after rollback leaves inconsistent cursor vs review-round-count
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `write-after` rollback decrements `review-round-count` but `write-cursor` keeps `ROUND_NUM`; `write-cursor` failure on rollback only warns. Gate C / Step 3 may see inconsistent count vs cursor after failed rollback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document invariant or fail closed when rollback write-cursor fails.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: assess-plan-round.sh touch undeclared in plan file list
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `resolve_workflow_path()` was refactored in `assess-plan-round.sh` to match the driver's classification alignment, but `assess-plan-round.sh` was not listed in the plan's "Files to modify/create". Behavior is consistent and low risk, but it is an undeclared touch surface for reviewers tracing only the plan file list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Either add a one-line note to the plan/helper contracts that assessor lane classification is shared, or leave as-is if umbrella #3133 already allows cross-helper alignment.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Duplicate json_scalar and workflow resolution across helpers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `json_scalar_or_sed` and workflow-path resolution logic is duplicated in `design-plan-quality-assessor.sh`, `assess-plan-round.sh`, and the SKILL jq block. Future rule changes require coordinated edits and risk assessor vs orchestrator drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Factor into lib-phase-driver or lib-run-params-json.sh; source from driver assess-plan-round and thin SKILL pre-read.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: assess-failed WARN prefix breaks two-step WARN= chat parity
- **Reviewer(s)**: dyn-assess-failed-propagation-output.txt
- **Severity**: latent
- **Concern**: `write-after-failed` uses the byte-stable operator sentence `**⚠ 3.6: failed to snapshot post-Gate-B plan…**` (via `WARN=` → file-read replay), but `assess-failed` WARN lines use the `**⚠ design-plan-quality-assessor: …**` prefix instead. That breaks the documented two-step `WARN=` chat contract parity with Step 2b/post-Gate-B snapshot failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-assess-failed-propagation-output.txt: Use `**⚠ 3.6: …**` prefixes for assess-failed WARN text (or document an explicit exception in `design-plan-quality-assessor.md` §Orchestrator handoff and `assessor.md` if the prefix change is intentional).


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Harness handoff mirror duplicates full SKILL handoff
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `apply_step3_6_handoff` in `test-design-plan-quality-assessor.sh` mirrors the full SKILL handoff (~100 lines). SKILL handoff edits may not be reflected in the harness until tests fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared handoff script or add stronger sync pins beyond abort strings.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Fragile _assessor_force_stdout substring detection
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `_assessor_force_stdout` is triggered by grepping a free-text substring in captured driver stdout. Unrelated stdout containing that substring could force stdout-only parse and drop file WARN replay.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Emit dedicated KV from driver on result-env write failure.
  - From cursor-specialist-correctness-output.txt: Emit an explicit RESULT_ENV_WRITE_OK (or similar) KV from the driver.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Non-HARD skip still invokes read-cursor
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Non-HARD skip path still invokes `read-cursor` in the driver, adding an extra child process on every SIMPLE design run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Skip read-cursor when WORKFLOW_PATH is not HARD; default ROUND_NUM=1.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

