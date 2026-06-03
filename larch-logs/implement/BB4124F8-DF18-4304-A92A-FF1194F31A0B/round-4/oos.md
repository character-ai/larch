### FINDING_29: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-shell-set-e-invariants-output.txt
- **Concern**: - **correctness** — The Step 3.6 `SKILL.md` fence correctly pairs `set +e` driver capture with `set -e` restoration before parse/abort (`skills/design/SKILL.md:1073-1140`); no defect found there relative to the scout checklist.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_30: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-shell-set-e-invariants-output.txt
- **Concern**: - **correctness** — Every wrapped `"$SNAPSHOT_SH"` / `"$ASSESS_SH"` / `append-tool-failure.sh` block in the driver captures rc before restoring `set -e` and reaches `_write_result_and_emit` on the intended settle paths when housekeeping above does not fail; child-call invariants match the `design-postplan-emit.sh` pattern.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_31: **correctness** `skills/design/scripts/test-assess-plan-round.sh:16-56` — The branch replaces `read_workflow_path` with `resolve_workflow_path` in `assess-plan-round.sh` (empty/missing `workflow_path` falls back to `design_classification`, mismatch aligns to `design_classification`), but this harness still only writes `workflow_path` via `write_params` and never references `design_classification`. `make test-assess-plan-round` therefore cannot catch drift between `assess-plan-round.sh` and `design-plan-quality-assessor.sh` on those branches when `assess-plan-round.sh` is exercised directly. **Suggested fix:** Add cases analogous to `test-design-plan-quality-assessor.sh` #19 (only `{"design_classification":"HARD"}`) and a mismatch fixture (`workflow_path` vs `design_classification`), asserting resolved HARD vs skipped behavior and emitted KVs.
- **Reviewer**: dyn-assess-round-regression-output.txt
- **Concern**: - **correctness** `skills/design/scripts/test-assess-plan-round.sh:16-56` — The branch replaces `read_workflow_path` with `resolve_workflow_path` in `assess-plan-round.sh` (empty/missing `workflow_path` falls back to `design_classification`, mismatch aligns to `design_classification`), but this harness still only writes `workflow_path` via `write_params` and never references `design_classification`. `make test-assess-plan-round` therefore cannot catch drift between `assess-plan-round.sh` and `design-plan-quality-assessor.sh` on those branches when `assess-plan-round.sh` is exercised directly. **Suggested fix:** Add cases analogous to `test-design-plan-quality-assessor.sh` #19 (only `{"design_classification":"HARD"}`) and a mismatch fixture (`workflow_path` vs `design_classification`), asserting resolved HARD vs skipped behavior and emitted KVs.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_32: [OUT_OF_SCOPE] No remaining `read_workflow_path` references in executable code (grep only hits historical `larch-logs/` review artifacts).
- **Reviewer**: dyn-assess-round-regression-output.txt
- **Concern**: - No remaining `read_workflow_path` references in executable code (grep only hits historical `larch-logs/` review artifacts).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_33: [OUT_OF_SCOPE] `resolve_workflow_path` in `skills/design/scripts/assess-plan-round.sh:38-56`, the pre-invoke block in `skills/design/SKILL.md:1051-1067`, and `skills/design/scripts/design-plan-quality-assessor.sh:108-125` use the same resolution rules (empty `workflow_path` → `HARD` only when `design_classification` is exactly `HARD`, else `SIMPLE`; when both are non-empty and differ, follow `design_classification`). The driver additionally emits a `WARN=` on mismatch; the orchestrator pre-read aligns silently, which is consistent because the driver warning is replayed via the handoff parse.
- **Reviewer**: dyn-assess-round-regression-output.txt
- **Concern**: - `resolve_workflow_path` in `skills/design/scripts/assess-plan-round.sh:38-56`, the pre-invoke block in `skills/design/SKILL.md:1051-1067`, and `skills/design/scripts/design-plan-quality-assessor.sh:108-125` use the same resolution rules (empty `workflow_path` → `HARD` only when `design_classification` is exactly `HARD`, else `SIMPLE`; when both are non-empty and differ, follow `design_classification`). The driver additionally emits a `WARN=` on mismatch; the orchestrator pre-read aligns silently, which is consistent because the driver warning is replayed via the handoff parse.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_34: [OUT_OF_SCOPE] `json_scalar_or_sed` is duplicated in `assess-plan-round.sh`, `design-plan-quality-assessor.sh`, and `design-postplan-emit.sh` with the same jq → sed → default behavior; command substitution strips trailing newlines, so `[[ … == HARD ]]` / `!= HARD` gates are not broken by `printf '%s\n'`.
- **Reviewer**: dyn-assess-round-regression-output.txt
- **Concern**: - `json_scalar_or_sed` is duplicated in `assess-plan-round.sh`, `design-plan-quality-assessor.sh`, and `design-postplan-emit.sh` with the same jq → sed → default behavior; command substitution strips trailing newlines, so `[[ … == HARD ]]` / `!= HARD` gates are not broken by `printf '%s\n'`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_35: [OUT_OF_SCOPE] Intentional behavior change (not a regression on normal runs): `design-init-runparams.sh` always writes both fields, but `run-params.json` with only `design_classification":"HARD"` now enters the HARD assessor lane; covered at the driver layer in `test-design-plan-quality-assessor.sh` #19, not in `test-assess-plan-round.sh`.
- **Reviewer**: dyn-assess-round-regression-output.txt
- **Concern**: - Intentional behavior change (not a regression on normal runs): `design-init-runparams.sh` always writes both fields, but `run-params.json` with only `design_classification":"HARD"` now enters the HARD assessor lane; covered at the driver layer in `test-design-plan-quality-assessor.sh` #19, not in `test-assess-plan-round.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_36: [OUT_OF_SCOPE] `skills/design/scripts/assess-plan-round.md:7` still describes only `workflow_path` gating and does not document the `design_classification` fallback added in this branch (doc drift only).
- **Reviewer**: dyn-assess-round-regression-output.txt
- **Concern**: - `skills/design/scripts/assess-plan-round.md:7` still describes only `workflow_path` gating and does not document the `design_classification` fallback added in this branch (doc drift only).
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_5: risk-integration: skills/design/scripts/test-assess-plan-round.sh:16-19
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] assess-plan-round.sh gained resolve_workflow_path() but its harness still only sets workflow_path. Empty or mismatched run-params can change skip vs HARD assess behavior without any failing test in make test-assess-plan-round. Add harness cases for design_classification-only HARD and workflow_path vs design_classification conflict; assert ASSESSOR_STATUS/VERDICT.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

