### FINDING_10: [OUT_OF_SCOPE] code-quality: skills/review/scripts/tally-code-votes.sh:286-293
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] static_focus_area retains structure and plan-fidelity mappings for retired static slugs. No functional impact on the new panel unless legacy output basenames reappear. Optional dead-arm cleanup in a follow-up.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_15: [OUT_OF_SCOPE] `skills/review/scripts/test-dispatch-panel.sh:638-640` still uses `static_slot_count=7` in `assert_emit_tally_panel` calls (`static-na`, `scout-ok`), which predates the 4-archetype / 8-row both-vendor layout and can hide telemetry regressions in `emit-tally.sh` even though dispatch counts were updated elsewhere.
- **Reviewer**: dyn-waterfall-output.txt
- **Concern**: - `skills/review/scripts/test-dispatch-panel.sh:638-640` still uses `static_slot_count=7` in `assert_emit_tally_panel` calls (`static-na`, `scout-ok`), which predates the 4-archetype / 8-row both-vendor layout and can hide telemetry regressions in `emit-tally.sh` even though dispatch counts were updated elsewhere.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-thresholds-output.txt
- **Concern**: - **code-quality** `skills/review/scripts/review-core.sh:530-542` — `dispatch_ok` and `static_dispatch_ok` are parsed from dispatch output but no longer influence threshold or early exit after removing the `STATIC_DISPATCH_OK=false` short-circuit; they are dead assignments unless a later consumer is added.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_20: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-thresholds-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/test-review-core.sh:113-126,254-260` — The review-core harness stubs `check-threshold.sh` and fabricates four `STATUS=OK` collector rows unconditionally, so it does not exercise real threshold argv (`--intended-slots`, `--dropped-slots-file`), dropped-peer recovery, or the coverage gate on both-down / Claude-fallback paths described in the plan’s `test-review-core` cases (#4, #8, #9).
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_22: **risk-integration** `skills/review/scripts/test-check-reviewer-failure-threshold.md:7-11` — The harness contract doc still describes the old 6-slot / 12-record threshold model (“6 fail of 12 records → over threshold (6-slot panel)”, “both-down … → 6 counted as failures”), while this branch rewrites `test-check-reviewer-failure-threshold.sh` for default `4`, explicit `8`, dropped-static accounting, and Codex dynamic-twin exclusion, and updates `check-reviewer-failure-threshold.md` accordingly. The sibling `.md` was not updated, so the documented coverage no longer matches the executable harness. **Suggested fix:** Rewrite the Coverage section to mirror the new script cases (4/8 denominators, 1-of-8 pass / 5-of-8 fail, `--dropped-slots-file`, dynamic Codex exclusion, never-launched padding rules).
- **Reviewer**: dyn-artifacts-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/test-check-reviewer-failure-threshold.md:7-11` — The harness contract doc still describes the old 6-slot / 12-record threshold model (“6 fail of 12 records → over threshold (6-slot panel)”, “both-down … → 6 counted as failures”), while this branch rewrites `test-check-reviewer-failure-threshold.sh` for default `4`, explicit `8`, dropped-static accounting, and Codex dynamic-twin exclusion, and updates `check-reviewer-failure-threshold.md` accordingly. The sibling `.md` was not updated, so the documented coverage no longer matches the executable harness. **Suggested fix:** Rewrite the Coverage section to mirror the new script cases (4/8 denominators, 1-of-8 pass / 5-of-8 fail, `--dropped-slots-file`, dynamic Codex exclusion, never-launched padding rules).
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_24: [OUT_OF_SCOPE] Pre-rendered sync for the folded agents looks correct: `agents/pre-rendered/.manifest` updates hashes for `reviewer-edge-cases-body.txt` and `reviewer-testing-body.txt`, and spot-checking those bodies against `agents/reviewer-edge-cases.md` / `agents/reviewer-testing.md` shows matching secondary-scan content. `reviewer-structure-body.txt` and `reviewer-plan-fidelity-body.txt` remain in the manifest because those agent files still exist; they are no longer static panel slots but are not stale relative to their sources.
- **Reviewer**: dyn-artifacts-output.txt
- **Concern**: - Pre-rendered sync for the folded agents looks correct: `agents/pre-rendered/.manifest` updates hashes for `reviewer-edge-cases-body.txt` and `reviewer-testing-body.txt`, and spot-checking those bodies against `agents/reviewer-edge-cases.md` / `agents/reviewer-testing.md` shows matching secondary-scan content. `reviewer-structure-body.txt` and `reviewer-plan-fidelity-body.txt` remain in the manifest because those agent files still exist; they are no longer static panel slots but are not stale relative to their sources.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_25: [OUT_OF_SCOPE] Topology/doc phrase migration is largely consistent on changed surfaces: `skills/shared/topology.tsv` splits value/composition, `docs/topology.md` is regenerated, `scripts/generate-topology-docs.sh` preamble matches, `skills/review/diagram.svg` uses the canonical phrase, and `test-quick-mode-docs-sync.sh` now greps the diagram for both presence and absence checks.
- **Reviewer**: dyn-artifacts-output.txt
- **Concern**: - Topology/doc phrase migration is largely consistent on changed surfaces: `skills/shared/topology.tsv` splits value/composition, `docs/topology.md` is regenerated, `scripts/generate-topology-docs.sh` preamble matches, `skills/review/diagram.svg` uses the canonical phrase, and `test-quick-mode-docs-sync.sh` now greps the diagram for both presence and absence checks.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_26: [OUT_OF_SCOPE] `scripts/test-quick-mode-docs-sync.md` still documents four positive anchors (`5 rounds`, `--panel hard`, etc.) while `POS_MARKERS` in the script only enforces two markers; that mismatch predates this branch (main already had only two array entries).
- **Reviewer**: dyn-artifacts-output.txt
- **Concern**: - `scripts/test-quick-mode-docs-sync.md` still documents four positive anchors (`5 rounds`, `--panel hard`, etc.) while `POS_MARKERS` in the script only enforces two markers; that mismatch predates this branch (main already had only two array entries).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_27: [OUT_OF_SCOPE] The branch’s second commit (`dbcc84e76`) is a `chore(larch-logs)` flush and is unrelated to the panel-collapse artifact sync work; it adds run-log bulk rather than changing runtime/generated contracts.
- **Reviewer**: dyn-artifacts-output.txt
- **Concern**: - The branch’s second commit (`dbcc84e76`) is a `chore(larch-logs)` flush and is unrelated to the panel-collapse artifact sync work; it adds run-log bulk rather than changing runtime/generated contracts.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_46: [OUT_OF_SCOPE] `review-core.sh` `static_archetype_coverage_ok` writes `$REVIEW_TMPDIR/static-success-slugs.txt` to a fixed path that is not in the `larch-log.sh` allow-list. Since the function is called only after `REVIEW_TMPDIR` is established and the collector file is verified, the coincidental guard prevents misuse, but it is not explicit. This is pre-existing design pattern, not introduced by this diff.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `review-core.sh` `static_archetype_coverage_ok` writes `$REVIEW_TMPDIR/static-success-slugs.txt` to a fixed path that is not in the `larch-log.sh` allow-list. Since the function is called only after `REVIEW_TMPDIR` is established and the collector file is verified, the coincidental guard prevents misuse, but it is not explicit. This is pre-existing design pattern, not introduced by this diff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_47: [OUT_OF_SCOPE] `is_dynamic_reviewer_basename` in `check-reviewer-failure-threshold.sh` correctly matches `dyn-*-codex-output.txt` via backtracking on the greedy `.*` in `^dyn-.*-output(-phase[23]|-retry)*\.txt$`; `is_dynamic_slot_name` correctly matches `dyn-*-codex` slot names. Both functions are correct as shipped.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `is_dynamic_reviewer_basename` in `check-reviewer-failure-threshold.sh` correctly matches `dyn-*-codex-output.txt` via backtracking on the greedy `.*` in `^dyn-.*-output(-phase[23]|-retry)*\.txt$`; `is_dynamic_slot_name` correctly matches `dyn-*-codex` slot names. Both functions are correct as shipped.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_48: [OUT_OF_SCOPE] The `codex-specialist-*-output.txt` deny rule in `larch-log.sh` is evaluated before the broad `*-output.txt` allow pattern in the case statement, so static Codex sidecar artifacts are correctly excluded. Dynamic Codex outputs (`dyn-*-codex-output.txt`) do not match the `codex-specialist-*` prefix pattern and remain allowed. No cross-contamination.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - The `codex-specialist-*-output.txt` deny rule in `larch-log.sh` is evaluated before the broad `*-output.txt` allow pattern in the case statement, so static Codex sidecar artifacts are correctly excluded. Dynamic Codex outputs (`dyn-*-codex-output.txt`) do not match the `codex-specialist-*` prefix pattern and remain allowed. No cross-contamination.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_49: [OUT_OF_SCOPE] `render-specialist-prompt.sh` — the `reviewer-testing` special case correctly injects plan/feature for all diff modes and description mode. The new branch key (`AGENT_BASENAME == "reviewer-testing"`) is orthogonal to the prior `$DIFF_MODE == "generic"` gate and poses no interaction risk for non-testing agents.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `render-specialist-prompt.sh` — the `reviewer-testing` special case correctly injects plan/feature for all diff modes and description mode. The new branch key (`AGENT_BASENAME == "reviewer-testing"`) is orthogonal to the prior `$DIFF_MODE == "generic"` gate and poses no interaction risk for non-testing agents. --- ```tsv id	file	line	severity	category	title F1	skills/review/SKILL.md	39	important	plan-fidelity	Step 2 not updated: stale Cursor-primary-only dynamic prose, missing 4-archetype static layout and Codex twin description F2	skills/review/scripts/test-review-core.sh	742	important	testing	Missing plan-required DROPPED_SLOTS_FILE integration test cases (#4, #8, #9, partial-dispatch-pass) F3	skills/review/scripts/test-tally-code-votes.sh	654	important	testing	Still exercises old 6-archetype topology; codex-specialist-* and dyn-*-codex attribution untested F4	skills/review/scripts/check-reviewer-failure-threshold.sh	135	latent	correctness	Never-launched padding suppressed by any dropped slot regardless of archetype; NEVER_LAUNCHED should subtract DROPPED_STATIC_SLOTS not zero out entirely F5	skills/review/scripts/review-core.sh	collect_dropped_static_outputs	nit	structure	O(N×M) nested manifest re-reads per dropped slot ```
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

