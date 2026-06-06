### FINDING_14: [OUT_OF_SCOPE] **Orphaned patch-apply helper still ships** — `skills/design/scripts/revise-plan-with-waterfall.sh` remains executable (now Makefile/agent-lint–only per comments). It still applies LLM-authored unified diffs via `git apply` when invoked directly. Step 3 no longer calls it and publish blocks `revise/` artifacts, but the helper is a latent footgun until the planned follow-up removal. Pre-existing surface, called out in SECURITY.md and the plan OOS list.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Orphaned patch-apply helper still ships** — `skills/design/scripts/revise-plan-with-waterfall.sh` remains executable (now Makefile/agent-lint–only per comments). It still applies LLM-authored unified diffs via `git apply` when invoked directly. Step 3 no longer calls it and publish blocks `revise/` artifacts, but the helper is a latent footgun until the planned follow-up removal. Pre-existing surface, called out in SECURITY.md and the plan OOS list.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] **Pause-time hygiene errors are swallowed** — `design-pause-save.sh` invokes `design-step3-state.sh --direct-review-pause-hygiene` with `>/dev/null 2>&1 || true`. Resume is still repaired on Step 3 entry via `--direct-review-entry`, so impact is limited to pause snapshot quality, not cross-user privilege escalation.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **Pause-time hygiene errors are swallowed** — `design-pause-save.sh` invokes `design-step3-state.sh --direct-review-pause-hygiene` with `>/dev/null 2>&1 || true`. Resume is still repaired on Step 3 entry via `--direct-review-entry`, so impact is limited to pause snapshot quality, not cross-user privilege escalation. ```tsv schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix ```
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] code-quality: skills/design/scripts/revise-plan-with-waterfall.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Orphaned inter-round revise helper remains in tree while Step 3 no longer calls it. Future contributors may assume auto-apply still exists or reintroduce loop coupling. Delete helper and tests in follow-up per plan out-of-scope note.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_27: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-drift-guard-logic-output.txt
- **Concern**: - **correctness** `skills/design/scripts/design-postplan-emit.sh:386-414` — Hard (12) → partition (13) → drift (14) precedence within `_postplan_finish_merged_plan_size` matches the plan and is covered by D33/D34; OR-combine drift logic, zero-baseline handling, write-once `lib-drift-baseline.sh`, and `DRIFT_*` / `BASELINE_*` initialization before early flush paths appear sound on the happy path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_31: [OUT_OF_SCOPE] The seven removed loop-only statuses (`converged`, `cap-hit`, `revision-failed`, `emit-plan-failed`, `optional-trailer-dedup-loss`, `plan-size-trigger`, `plan-validator-defects`) appear fully scrubbed from live `skills/design/` routing prose (`approval-gates.md`, `decompose-panel.md`, `plan-review.md`, `SKILL.md` branch matrix). Remaining hits are intentional harness normalization cases (`test-run-step3-review.sh`, `test-step3-review-cap.sh`, `test-step3-orchestrator-fence.sh`) or unrelated `*.cap-hit` sidecar filename patterns.
- **Reviewer**: dyn-state-transition-cleanup-output.txt
- **Concern**: - The seven removed loop-only statuses (`converged`, `cap-hit`, `revision-failed`, `emit-plan-failed`, `optional-trailer-dedup-loss`, `plan-size-trigger`, `plan-validator-defects`) appear fully scrubbed from live `skills/design/` routing prose (`approval-gates.md`, `decompose-panel.md`, `plan-review.md`, `SKILL.md` branch matrix). Remaining hits are intentional harness normalization cases (`test-run-step3-review.sh`, `test-step3-review-cap.sh`, `test-step3-orchestrator-fence.sh`) or unrelated `*.cap-hit` sidecar filename patterns.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_32: [OUT_OF_SCOPE] Single-pass terminal ordering in `plan-review-loop.sh:1504-1560` matches the plan spec for the paths that reach it: `panel-failed` is forced on nonzero round rc or in-function `panel-failed` before collector fallback; `main-agent-vote-required` and fatal `tally-error` short-circuit before `_accumulate_round_oos`; `degraded-empty-collector` is checked before `zero-findings-degraded-panel`. Harness coverage in `test-plan-review-loop.sh` exercises those branches.
- **Reviewer**: dyn-state-transition-cleanup-output.txt
- **Concern**: - Single-pass terminal ordering in `plan-review-loop.sh:1504-1560` matches the plan spec for the paths that reach it: `panel-failed` is forced on nonzero round rc or in-function `panel-failed` before collector fallback; `main-agent-vote-required` and fatal `tally-error` short-circuit before `_accumulate_round_oos`; `degraded-empty-collector` is checked before `zero-findings-degraded-panel`. Harness coverage in `test-plan-review-loop.sh` exercises those branches.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_33: [OUT_OF_SCOPE] `design-step3-state.sh` centralizes Gate-B-bypass sentinel writes consistently with `skills/design/SKILL.md` branch-matrix prose; `scripts/test-design-structure.sh` pins against inline sentinel writes in that section.
- **Reviewer**: dyn-state-transition-cleanup-output.txt
- **Concern**: - `design-step3-state.sh` centralizes Gate-B-bypass sentinel writes consistently with `skills/design/SKILL.md` branch-matrix prose; `scripts/test-design-structure.sh` pins against inline sentinel writes in that section.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_5: architecture: skills/design/scripts/lib-drift-baseline.sh:18
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] larch_drift_baseline_write_once skips writes when any path exists (-e), not only regular files (-f). A symlink at drift-baseline.env can block seeding until a later cleanup branch, making baseline creation order-dependent. Match the documented [[ ! -f ... ]] guard or document and test symlink behavior explicitly.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

