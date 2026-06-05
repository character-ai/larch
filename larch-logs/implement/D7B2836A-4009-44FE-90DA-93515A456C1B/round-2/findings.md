### FINDING_1: code-quality: skills/design/SKILL.md:651
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 2a still claims review_budget quick skips the Step 2b plan-command validator. An orchestrator on a quick-tier run may skip or deprioritize validation despite design-postplan-emit.sh always invoking invoke-plan-validator.sh. Remove or rewrite the Step 2b validator clause; keep review_budget only for Step 3 panel gating if still accurate.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/design/scripts/plan-review-loop.sh:600-610
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] partition_requested parsing duplicates jq/sed logic instead of sharing json_boolean_or_sed. Future run-params parsing changes could diverge between merged driver rc13 and plan-review-loop partition handoff. Extract json_boolean_or_sed to a shared sourced helper and use it in plan-review-loop.sh.
- **Suggested revision**: Address the concern above.

### FINDING_3: risk-integration: skills/design/SKILL.md:874
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Intermediate prose still says to continue after Step 2b.5 completes on the main path. Operators or agents may run redundant standalone Step 2b.5 after a clean merged driver exit 0. Say the merged --with-plan-size driver must settle first; reference standalone Step 2b.5 only for Override and plan-review-loop paths.
- **Suggested revision**: Address the concern above.

### FINDING_4: architecture: skills/design/references/approval-gates.md:157-158
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Gate B relies on prose delegation to SKILL Step 2b case arms without a pinned inline fence. Gate B re-emit may omit echo/case arms or use wrong site-specific Override/sentinel behavior. Embed site-specific case arms in approval-gates.md or run assert_postplan_thin_fence on that section.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/design/scripts/design-postplan-emit.sh:47-58
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] json_boolean_or_sed sed fallback uses greedy .* before the key name. Unusual run-params.json formatting could yield a false partition_requested value without jq. Use line-anchored sed or require jq for boolean fields.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/test-design-structure.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit]  No negative self-test for assert_postplan_thin_fence missing *) arm. Regressions could remove default-abort without CI catching it. Add a postplan thin-fence negative fixture like the Step 3.6 self-tests.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: (branch)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Branch diff bundles Phase 4 with OOS materialization release Step 7 publish fixes and other PRs. Reviewers may miss Phase 4 regressions among unrelated changes. Split PR or document commit ranges in the PR body.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/design/SKILL.md:874
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 2b prose says continue after standalone Step 2b.5 while the next block runs merged --with-plan-size. Orchestrator runs retained Step 2b.5 after a clean merged emit, duplicating plan-size checks or prompts. Reword to continue after merged driver completes; reserve standalone 2b.5 for Override and retained callers only.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/design/SKILL.md:1124
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Gate B intro still mandates Step 2b.5 after every design-postplan-emit re-emit. Gate B clean path runs standalone 2b.5 despite approval-gates merged-fence contract. Match approval-gates.md: --with-plan-size on re-emit; standalone 2b.5 only on Override.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/design/SKILL.md:651
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 2a claims review_budget quick skips Step 2b validator. Misleading for operators; script always validates on --with-plan-size. State review_budget gates Step 3 only; Step 2b validation is unconditional.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/design/SKILL.md:984-985
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Step 2b.5 boundary still says continue after 2b.5 returns on initial path. Conflicts with rc 0 sentinel writes inside merged fence without standalone procedure. Tie initial continue to _postplan_rc=0 or sentinel writes in thin fence.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/test-design-structure.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] No negative assert_postplan_thin_fence self-test for missing case arm. Regression could drop *) or rc arm without CI failure. Add fixture like run_thin_fence_self_tests for postplan fences.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/design/SKILL.md:651
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 2a still documents review_budget gating Step 2b validation after review_budget was removed from run-params and validation became unconditional in design-postplan-emit.sh. Orchestrator on a fresh run may believe quick/SIMPLE skips plan-command validation and not expect rc10 defect handling from the merged driver. Remove review_budget from Step 2a; state unconditional validation via design-postplan-emit.sh / flags.md contract.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: skills/design/SKILL.md:1124
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 3.5 Gate B prose still requires standalone Step 2b.5 after every design-postplan-emit re-emit. After Gate B plan revision on the merged clean path, an orchestrator following Step 3.5 may run standalone Step 2b.5 again (duplicate prompts / wrong sentinels) instead of proceeding from _postplan_rc=0 to Step 3.6. Rewrite Step 3.5 Gate B intro to match merged --with-plan-size flow; reserve standalone Step 2b.5 for Override and retained callers only.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: skills/design/SKILL.md:651
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 2a still documents review_budget quick-skip for Step 2b validation. The driver always validates; stale prose can mislead the orchestrator or future edits into reintroducing a skip path removed from write-run-params and flags.md. Remove or rewrite the review_budget sentence to state unconditional validation via design-postplan-emit.sh.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: skills/design/SKILL.md:1397
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 5c still gates composed-plan validation on review_budget != quick while Step 2b validation is unconditional. Legacy run-params with review_budget=quick could skip Step 5c validation while plan.txt was validated in Step 2b, producing inconsistent publish behavior. Align Step 5c validation prose and behavior with unconditional validation, or document and test an explicit composed-plan exception.
- **Suggested revision**: Address the concern above.

### FINDING_17: architecture: scripts/test-design-structure.sh:89-296
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan-required negative self-test for assert_postplan_thin_fence missing a mandatory rc arm is not implemented. A future edit can drop a case arm from the Step 2b fence without CI catching it, unlike Step 3.6 thin-fence self-tests. Add run_postplan_thin_fence_self_tests with a fixture missing one rc arm and assert the helper fails.
- **Suggested revision**: Address the concern above.

### FINDING_18: architecture: scripts/test-design-structure.sh:560-627
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan acceptance listed extensive sentinel and multi-site postplan thin-fence pins; only Step 2b rc0 step-2b.5 and partial Gate B/discussion greps are pinned. Initial rc12 Split entry, Refine/no-split Continue sentinels, Gate B Override sentinel, and plan-size-trigger initial-site step-2b rules can regress without structure-test failure. Add the planned sentinel pins and scoped assert_postplan_thin_fence coverage for Gate B, discussion-round2, Step 1e, and decompose-panel.
- **Suggested revision**: Address the concern above.

### FINDING_19: architecture: Plan §Exit-code contract / skills/design/references/discussion-rounds.md:126
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Plan pins --with-plan-size --force-validate; implementation retires --force-validate and makes validation unconditional. Plan-to-implementation traceability fails; operators following the plan argv may look for a removed flag. Update plan/acceptance docs to --with-plan-size only, or restore compat --force-validate if the written contract must remain.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] risk-integration: Branch diff (non-Phase-4 files)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Diff includes release, OOS pipeline, SECURITY, ship-pr, and other commits beyond Phase 4 scope. Phase 4 plan fidelity review cannot attest those changes; they need separate plan/issue review. Review under their owning issues/plans.
- **Suggested revision**: Address the concern above.

### FINDING_21: **correctness** `skills/design/references/decompose-panel.md:80,123` — Stage 0 **Refine plan myself** and §6 **Continue** (no-split consensus) say only “return to the caller” with no adjacent `mkdir` / `: > .completed/step-2b.5` (or initial-site `step-2b`) instructions. The obligation lives only in §9 (line 195), far from the operator-choice bullets. An orchestrator following §4→§6 sequentially can resume after **Continue** or early **Refine** without ever writing `step-2b.5`, leaving `design-pause-save.sh`’s registry walk stuck at `2b.5` while the run has already advanced (e.g. into Step 3). **Suggested fix:** Add the same sentinel-write sentence to the §4 Stage 0 Refine bullet and the §6 **Continue** bullet (site-aware: `step-2b` + `step-2b.5` for initial-site merged callers; `step-2b.5` only for Gate B / discussion / retained `plan-size-trigger`), matching §9.
- **Reviewer**: dyn-sentinel-writes-output.txt
- **Concern**: - **correctness** `skills/design/references/decompose-panel.md:80,123` — Stage 0 **Refine plan myself** and §6 **Continue** (no-split consensus) say only “return to the caller” with no adjacent `mkdir` / `: > .completed/step-2b.5` (or initial-site `step-2b`) instructions. The obligation lives only in §9 (line 195), far from the operator-choice bullets. An orchestrator following §4→§6 sequentially can resume after **Continue** or early **Refine** without ever writing `step-2b.5`, leaving `design-pause-save.sh`’s registry walk stuck at `2b.5` while the run has already advanced (e.g. into Step 3). **Suggested fix:** Add the same sentinel-write sentence to the §4 Stage 0 Refine bullet and the §6 **Continue** bullet (site-aware: `step-2b` + `step-2b.5` for initial-site merged callers; `step-2b.5` only for Gate B / discussion / retained `plan-size-trigger`), matching §9.
- **Suggested revision**: Address the concern above.

### FINDING_22: **correctness** `skills/design/references/approval-gates.md:157-158` and `skills/design/SKILL.md:941` — Gate B’s shared post-apply pipeline tells the orchestrator to reuse the Step 2b thin-fence `case` (rc **12**/**13** only touch `step-2b`), then handle Gate B in separate step-8 prose (rc **12** **Override** must write `step-2b.5` before Step 3.6; non-exiting Split writes `step-2b.5`). Immediately after the only embedded `case` fence, `SKILL.md` still documents rc **12** as initial-site **Split/Cancel only** (no Override) and does not mention the Gate B Override sentinel. A Gate B path that runs the shared `case` and then follows `SKILL.md:941` can skip the Override arm and the `step-2b.5` write required before Step 3.6. **Suggested fix:** Scope `SKILL.md:941` explicitly to initial Step 2b (or add a parallel Gate B post-`case` block in `approval-gates.md` that duplicates Override + sentinel writes), and embed one fenced `case`+post-`case` sequence for Gate B so Override cannot be dropped.
- **Reviewer**: dyn-sentinel-writes-output.txt
- **Concern**: - **correctness** `skills/design/references/approval-gates.md:157-158` and `skills/design/SKILL.md:941` — Gate B’s shared post-apply pipeline tells the orchestrator to reuse the Step 2b thin-fence `case` (rc **12**/**13** only touch `step-2b`), then handle Gate B in separate step-8 prose (rc **12** **Override** must write `step-2b.5` before Step 3.6; non-exiting Split writes `step-2b.5`). Immediately after the only embedded `case` fence, `SKILL.md` still documents rc **12** as initial-site **Split/Cancel only** (no Override) and does not mention the Gate B Override sentinel. A Gate B path that runs the shared `case` and then follows `SKILL.md:941` can skip the Override arm and the `step-2b.5` write required before Step 3.6. **Suggested fix:** Scope `SKILL.md:941` explicitly to initial Step 2b (or add a parallel Gate B post-`case` block in `approval-gates.md` that duplicates Override + sentinel writes), and embed one fenced `case`+post-`case` sequence for Gate B so Override cannot be dropped.
- **Suggested revision**: Address the concern above.

### FINDING_23: **correctness** `skills/design/SKILL.md:967,1087` — Retained Step 2b.5 step 5 (`PARTITION_REQUESTED=true`) jumps straight into Split-path with no `step-2b.5` write at branch entry. `LOOP_STATUS=plan-size-trigger` from `plan-review-loop.sh` runs this full procedure; partition routing therefore enters decomposition without marking `2b.5` complete. A §6 **Continue** (no-split) return then reaches Step 3 with `step-2b` possibly set from an earlier initial rc **12**/**13** `case` arm but `step-2b.5` still absent unless §9 is applied. **Suggested fix:** Before “run **Split-path** below” in step 5 (and/or at the start of the `plan-size-trigger` handler), write/update `: > "$DESIGN_TMPDIR/.completed/step-2b.5"` for retained callers (plus `: > step-2b` when the handoff is initial-site), and repeat the requirement on the §6 **Continue** bullet in `decompose-panel.md`.
- **Reviewer**: dyn-sentinel-writes-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:967,1087` — Retained Step 2b.5 step 5 (`PARTITION_REQUESTED=true`) jumps straight into Split-path with no `step-2b.5` write at branch entry. `LOOP_STATUS=plan-size-trigger` from `plan-review-loop.sh` runs this full procedure; partition routing therefore enters decomposition without marking `2b.5` complete. A §6 **Continue** (no-split) return then reaches Step 3 with `step-2b` possibly set from an earlier initial rc **12**/**13** `case` arm but `step-2b.5` still absent unless §9 is applied. **Suggested fix:** Before “run **Split-path** below” in step 5 (and/or at the start of the `plan-size-trigger` handler), write/update `: > "$DESIGN_TMPDIR/.completed/step-2b.5"` for retained callers (plus `: > step-2b` when the handoff is initial-site), and repeat the requirement on the §6 **Continue** bullet in `decompose-panel.md`.
- **Suggested revision**: Address the concern above.

### FINDING_24: **correctness** `scripts/test-design-structure.sh:760-761,1262-1270` — The branch adds `assert_postplan_thin_fence` for Step 2b rc **0** `step-2b.5` only and Check 19 pins `decompose-panel-dispatch.sh`, not the plan’s sentinel matrix (initial rc **12**/**13** entry `step-2b`, Refine/no-split **Continue** dual writes, Gate B rc **12** Override `step-2b.5`, `decompose-panel.md` non-exiting rules, `plan-size-trigger` Refine→Gate A). Doc drift above is therefore unguarded by structure tests. **Suggested fix:** Extend `test-design-structure.sh` with the sentinel pins from the plan (grep `approval-gates.md`, `discussion-rounds.md`, `decompose-panel.md`, and Step 3 `plan-size-trigger` prose) so missing or mis-scoped writes fail CI.
- **Reviewer**: dyn-sentinel-writes-output.txt
- **Concern**: - **correctness** `scripts/test-design-structure.sh:760-761,1262-1270` — The branch adds `assert_postplan_thin_fence` for Step 2b rc **0** `step-2b.5` only and Check 19 pins `decompose-panel-dispatch.sh`, not the plan’s sentinel matrix (initial rc **12**/**13** entry `step-2b`, Refine/no-split **Continue** dual writes, Gate B rc **12** Override `step-2b.5`, `decompose-panel.md` non-exiting rules, `plan-size-trigger` Refine→Gate A). Doc drift above is therefore unguarded by structure tests. **Suggested fix:** Extend `test-design-structure.sh` with the sentinel pins from the plan (grep `approval-gates.md`, `discussion-rounds.md`, `decompose-panel.md`, and Step 3 `plan-size-trigger` prose) so missing or mis-scoped writes fail CI.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] **Initial Step 2b embedded fence** (`skills/design/SKILL.md:889-936`) matches the plan for rc **0** (both sentinels), rc **12**/**13** entry (`step-2b` only), rc **10** Override prose (`step-2b` then retained Step 2b.5), and non-exiting Split (`step-2b` + `step-2b.5` at line 941). Pause/resume via `design-pause-save.sh` walking `step-name-registry.tsv` will correctly target `2b.5` when only `step-2b` was set (e.g. hard-trigger entry then cancel)—that is consistent, not a missing write.
- **Reviewer**: dyn-sentinel-writes-output.txt
- **Concern**: - **Initial Step 2b embedded fence** (`skills/design/SKILL.md:889-936`) matches the plan for rc **0** (both sentinels), rc **12**/**13** entry (`step-2b` only), rc **10** Override prose (`step-2b` then retained Step 2b.5), and non-exiting Split (`step-2b` + `step-2b.5` at line 941). Pause/resume via `design-pause-save.sh` walking `step-name-registry.tsv` will correctly target `2b.5` when only `step-2b` was set (e.g. hard-trigger entry then cancel)—that is consistent, not a missing write.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] **`discussion-rounds.md`** correctly limits discussion rc **12**/**13** non-exiting returns to `step-2b.5` only (no initial-site `step-2b` on entry), but telling implementers to reuse the “full Step 2b” `case` arms still runs rc **12**/**13** arms that write `step-2b`; that is redundant, not a resume hole.
- **Reviewer**: dyn-sentinel-writes-output.txt
- **Concern**: - **`discussion-rounds.md`** correctly limits discussion rc **12**/**13** non-exiting returns to `step-2b.5` only (no initial-site `step-2b` on entry), but telling implementers to reuse the “full Step 2b” `case` arms still runs rc **12**/**13** arms that write `step-2b`; that is redundant, not a resume hole.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] **Commits on branch:** `07e42d57c` (merge `--with-plan-size` + thin fence), `d31536913` (review follow-up); earlier commits in the range are unrelated release/implement work.
- **Reviewer**: dyn-sentinel-writes-output.txt
- **Concern**: - **Commits on branch:** `07e42d57c` (merge `--with-plan-size` + thin fence), `d31536913` (review follow-up); earlier commits in the range are unrelated release/implement work.
- **Suggested revision**: Address the concern above.

### FINDING_28: **correctness** `skills/design/SKILL.md:1124` — Step 3.5 still tells the orchestrator that Gate B “requires **Step 2b.5** immediately after each settled `design-postplan-emit.sh` re-emit” and that continuation needs “**and Step 2b.5 returns**” before Step 3.6. That contradicts the merged contract in the same file (`--with-plan-size` folds plan-size into the driver; `approval-gates.md` §Shared post-apply steps 7–9 route clean `_postplan_rc=0` to Step 3.6 after only updating `.completed/step-2b.5`). An executor that treats the Step 3.5 intro as authoritative can run the standalone Step 2b.5 procedure after a merged `rc=0`, duplicating `check-plan-size.sh` and bypassing the thin-fence `rc` mapping (`10`/`12`/`13`). **Suggested fix:** Rewrite Step 3.5 Gate B intro to match `approval-gates.md`: merged post-apply uses `design-postplan-emit.sh --with-plan-size` + `printf` + `case "${_postplan_rc:-1}"`; standalone Step 2b.5 is only for Override-after-defects, `LOOP_STATUS=plan-size-trigger`, and `plan-review-loop.sh` handoffs; passive-summary paths skip re-emit entirely.
- **Reviewer**: dyn-exit-code-precedence-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:1124` — Step 3.5 still tells the orchestrator that Gate B “requires **Step 2b.5** immediately after each settled `design-postplan-emit.sh` re-emit” and that continuation needs “**and Step 2b.5 returns**” before Step 3.6. That contradicts the merged contract in the same file (`--with-plan-size` folds plan-size into the driver; `approval-gates.md` §Shared post-apply steps 7–9 route clean `_postplan_rc=0` to Step 3.6 after only updating `.completed/step-2b.5`). An executor that treats the Step 3.5 intro as authoritative can run the standalone Step 2b.5 procedure after a merged `rc=0`, duplicating `check-plan-size.sh` and bypassing the thin-fence `rc` mapping (`10`/`12`/`13`). **Suggested fix:** Rewrite Step 3.5 Gate B intro to match `approval-gates.md`: merged post-apply uses `design-postplan-emit.sh --with-plan-size` + `printf` + `case "${_postplan_rc:-1}"`; standalone Step 2b.5 is only for Override-after-defects, `LOOP_STATUS=plan-size-trigger`, and `plan-review-loop.sh` handoffs; passive-summary paths skip re-emit entirely.
- **Suggested revision**: Address the concern above.

### FINDING_29: **correctness** `skills/design/SKILL.md:1096` — The Step 3 → Gate B handoff says “Whenever Gate B does revise the plan, it runs `design-postplan-emit.sh`” without `--with-plan-size`. Legacy (non-flag) mode exits `0` on `VALIDATE_STATUS=defects-found` and never emits action codes `10`/`12`/`13`, so an orchestrator following this line can miss defects-before-plan-size precedence and hard/partition routing. **Suggested fix:** Name `design-postplan-emit.sh --with-plan-size` explicitly here (or point to `approval-gates.md` §Shared post-apply step 7 as the only Gate B re-emit entry).
- **Reviewer**: dyn-exit-code-precedence-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:1096` — The Step 3 → Gate B handoff says “Whenever Gate B does revise the plan, it runs `design-postplan-emit.sh`” without `--with-plan-size`. Legacy (non-flag) mode exits `0` on `VALIDATE_STATUS=defects-found` and never emits action codes `10`/`12`/`13`, so an orchestrator following this line can miss defects-before-plan-size precedence and hard/partition routing. **Suggested fix:** Name `design-postplan-emit.sh --with-plan-size` explicitly here (or point to `approval-gates.md` §Shared post-apply step 7 as the only Gate B re-emit entry).
- **Suggested revision**: Address the concern above.

### FINDING_30: **correctness** `skills/design/references/approval-gates.md:157-158`, `skills/design/references/discussion-rounds.md:126` — Gate B and discussion-round2 describe the thin fence (“same `case` arms as `SKILL.md` Step 2b” / “full Step 2b thin-fence `case`”) but do not include an executable fenced `case "${_postplan_rc:-1}" in` block with the mandatory `*)` arm. Only `skills/design/SKILL.md` Step 2b has the real fence; `scripts/test-design-structure.sh` runs `assert_postplan_thin_fence` only on that region (line 560), not on Gate B or discussion. An orchestrator reading only the reference during Gate B can call the driver, print output, and never dispatch on `10`/`11`/`12`/`13`—a silent routing failure the plan explicitly guarded against. **Suggested fix:** Either embed a copy of the Step 2b fence in each merged site (with site-specific prose after `esac`), or add a normative “MUST paste the Step 2b bash fence verbatim before step 8” directive plus structure-test `assert_postplan_thin_fence` on scoped regions of `approval-gates.md` and `discussion-rounds.md`.
- **Reviewer**: dyn-exit-code-precedence-output.txt
- **Concern**: - **correctness** `skills/design/references/approval-gates.md:157-158`, `skills/design/references/discussion-rounds.md:126` — Gate B and discussion-round2 describe the thin fence (“same `case` arms as `SKILL.md` Step 2b” / “full Step 2b thin-fence `case`”) but do not include an executable fenced `case "${_postplan_rc:-1}" in` block with the mandatory `*)` arm. Only `skills/design/SKILL.md` Step 2b has the real fence; `scripts/test-design-structure.sh` runs `assert_postplan_thin_fence` only on that region (line 560), not on Gate B or discussion. An orchestrator reading only the reference during Gate B can call the driver, print output, and never dispatch on `10`/`11`/`12`/`13`—a silent routing failure the plan explicitly guarded against. **Suggested fix:** Either embed a copy of the Step 2b fence in each merged site (with site-specific prose after `esac`), or add a normative “MUST paste the Step 2b bash fence verbatim before step 8” directive plus structure-test `assert_postplan_thin_fence` on scoped regions of `approval-gates.md` and `discussion-rounds.md`.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] **Driver precedence (verified sound):** In `design-postplan-emit.sh`, `VALIDATE_STATUS=defects-found` exits `10` before plan-size (`521-526`); hard is checked before partition in `_postplan_finish_merged_plan_size` (`363-375`); pause returns `11` after result-env flush (`422-425`). Harness cases cover defects→10, partition+hard→12, partition without jq→13, rc2/3→0 nonfatal (`test-design-postplan-emit.sh` D19–D22).
- **Reviewer**: dyn-exit-code-precedence-output.txt
- **Concern**: - **Driver precedence (verified sound):** In `design-postplan-emit.sh`, `VALIDATE_STATUS=defects-found` exits `10` before plan-size (`521-526`); hard is checked before partition in `_postplan_finish_merged_plan_size` (`363-375`); pause returns `11` after result-env flush (`422-425`). Harness cases cover defects→10, partition+hard→12, partition without jq→13, rc2/3→0 nonfatal (`test-design-postplan-emit.sh` D19–D22).
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] **Initial Step 2b fence (verified sound):** Executable fence has arms `0`, `10`, `11`, `12`, `13`, `2`, `1`, and `*)` (`skills/design/SKILL.md:889-935`); legacy fat-fence `_postplan_rc` 0/1-only guards were removed in this branch.
- **Reviewer**: dyn-exit-code-precedence-output.txt
- **Concern**: - **Initial Step 2b fence (verified sound):** Executable fence has arms `0`, `10`, `11`, `12`, `13`, `2`, `1`, and `*)` (`skills/design/SKILL.md:889-935`); legacy fat-fence `_postplan_rc` 0/1-only guards were removed in this branch.
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] **`plan-review-loop.sh` partition gating:** Direct `check-plan-size.sh` rc 2/3 returns early before `LOOP_STATUS=plan-size-trigger` (`617-641`), matching Step 2b.5 step 3 semantics.
- **Reviewer**: dyn-exit-code-precedence-output.txt
- **Concern**: - **`plan-review-loop.sh` partition gating:** Direct `check-plan-size.sh` rc 2/3 returns early before `LOOP_STATUS=plan-size-trigger` (`617-641`), matching Step 2b.5 step 3 semantics.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] **Plan vs implementation:** The issue plan pins `--with-plan-size --force-validate` for discussion/Step 1e; the branch deliberately retires `--force-validate` (`test-design-structure.sh:621-623`, `test-design-postplan-emit.sh` D12). That is a spec drift choice, not an exit-code precedence bug.
- **Reviewer**: dyn-exit-code-precedence-output.txt
- **Concern**: - **Plan vs implementation:** The issue plan pins `--with-plan-size --force-validate` for discussion/Step 1e; the branch deliberately retires `--force-validate` (`test-design-structure.sh:621-623`, `test-design-postplan-emit.sh` D12). That is a spec drift choice, not an exit-code precedence bug.
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] **Pre-existing Gate B prose tension:** Passive-summary auto-continue vs “Step 2b.5 returns” predates this branch; `approval-gates.md` already treats passive-summary as skipping re-emit (not worsened by the driver merge).
- **Reviewer**: dyn-exit-code-precedence-output.txt
- **Concern**: - **Pre-existing Gate B prose tension:** Passive-summary auto-continue vs “Step 2b.5 returns” predates this branch; `approval-gates.md` already treats passive-summary as skipping re-emit (not worsened by the driver merge).
- **Suggested revision**: Address the concern above.

### FINDING_36: **architecture** `skills/design/references/approval-gates.md:157-158` — Step 7 tells Gate B to reuse the Step 2b `case "${_postplan_rc:-1}" in` arms verbatim, but those arms are initial-site specific: rc `0` writes both `.completed/step-2b` and `.completed/step-2b.5`, and rc `12`/`13` write `.completed/step-2b`. Step 8 then requires Gate B–specific behavior (rc `0` → step-2b.5 only; rc `12` → Split/Override/Cancel; no step-2b sentinel). An orchestrator that follows step 7 literally will mark the wrong completion sentinels on Gate B re-emits, breaking pause/resume and step replay. **Suggested fix:** Replace “same case arms as Step 2b” with a Gate B–specific fenced block (or a parameterized variant) whose rc `0`/`12`/`13` arms match step 8; pin it with `assert_postplan_thin_fence` on the Gate B shared post-apply region.
- **Reviewer**: dyn-reentry-env-reads-output.txt
- **Concern**: - **architecture** `skills/design/references/approval-gates.md:157-158` — Step 7 tells Gate B to reuse the Step 2b `case "${_postplan_rc:-1}" in` arms verbatim, but those arms are initial-site specific: rc `0` writes both `.completed/step-2b` and `.completed/step-2b.5`, and rc `12`/`13` write `.completed/step-2b`. Step 8 then requires Gate B–specific behavior (rc `0` → step-2b.5 only; rc `12` → Split/Override/Cancel; no step-2b sentinel). An orchestrator that follows step 7 literally will mark the wrong completion sentinels on Gate B re-emits, breaking pause/resume and step replay. **Suggested fix:** Replace “same case arms as Step 2b” with a Gate B–specific fenced block (or a parameterized variant) whose rc `0`/`12`/`13` arms match step 8; pin it with `assert_postplan_thin_fence` on the Gate B shared post-apply region.
- **Suggested revision**: Address the concern above.

### FINDING_37: **architecture** `skills/design/references/discussion-rounds.md:126` — The Round 2 re-emit paragraph has the same conflict: it requires the “full Step 2b thin-fence `case` arms” while also saying rc `0` must write only `.completed/step-2b.5` and rc `12`/`13` must use discussion Split/Cancel (no initial-site step-2b writes). Copying Step 2b’s bash `case` block would write step-2b on rc `0`/`12`/`13`, contradicting the site contract and the decompose-panel sentinel rules. **Suggested fix:** Give discussion-round2 its own pinned thin fence (or explicit “adapt arms 0/12/13” rules) instead of delegating to Step 2b’s literal `case` bodies; extend `assert_postplan_thin_fence` to that section.
- **Reviewer**: dyn-reentry-env-reads-output.txt
- **Concern**: - **architecture** `skills/design/references/discussion-rounds.md:126` — The Round 2 re-emit paragraph has the same conflict: it requires the “full Step 2b thin-fence `case` arms” while also saying rc `0` must write only `.completed/step-2b.5` and rc `12`/`13` must use discussion Split/Cancel (no initial-site step-2b writes). Copying Step 2b’s bash `case` block would write step-2b on rc `0`/`12`/`13`, contradicting the site contract and the decompose-panel sentinel rules. **Suggested fix:** Give discussion-round2 its own pinned thin fence (or explicit “adapt arms 0/12/13” rules) instead of delegating to Step 2b’s literal `case` bodies; extend `assert_postplan_thin_fence` to that section.
- **Suggested revision**: Address the concern above.

### FINDING_38: **architecture** `skills/design/SKILL.md:636` — Step 1e’s optional-trailer guard delegates to “Step 2b thin-fence `case` arms” for the merged fence but specifies post-rc behavior that differs from Step 2b (rc `0` → step-2b.5 only before Gate A; rc `10` → shared validator failure without calling out allowlisted result-env reads). Unlike the Step 2b fence (`skills/design/SKILL.md:895-911`), Step 1e has no executable allowlisted-read loop and no “never `source`” pin, so rc `10` Fix-and-retry/Override can run without fresh `VALIDATE_*` keys from `.design-postplan-emit-result.env`. **Suggested fix:** Either reference a discussion-round2 fence that includes the rc `10` allowlisted read (with symlink refusal), or add the same allowlisted key-extraction block to Step 1e and pin it in `test-design-structure.sh`.
- **Reviewer**: dyn-reentry-env-reads-output.txt
- **Concern**: - **architecture** `skills/design/SKILL.md:636` — Step 1e’s optional-trailer guard delegates to “Step 2b thin-fence `case` arms” for the merged fence but specifies post-rc behavior that differs from Step 2b (rc `0` → step-2b.5 only before Gate A; rc `10` → shared validator failure without calling out allowlisted result-env reads). Unlike the Step 2b fence (`skills/design/SKILL.md:895-911`), Step 1e has no executable allowlisted-read loop and no “never `source`” pin, so rc `10` Fix-and-retry/Override can run without fresh `VALIDATE_*` keys from `.design-postplan-emit-result.env`. **Suggested fix:** Either reference a discussion-round2 fence that includes the rc `10` allowlisted read (with symlink refusal), or add the same allowlisted key-extraction block to Step 1e and pin it in `test-design-structure.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_39: **architecture** `skills/design/SKILL.md:895-911` — The only merged fence with an executable allowlisted result-env read is initial Step 2b; Gate B and discussion-round2 rely on prose. The read uses a hand-rolled `while`/`printf -v` loop instead of `phase_driver_read_result_env` from `skills/design/scripts/lib-phase-driver.sh:66-91`, which is the repo’s normative allowlisted parser (symlink refusal plus multiline-value rejection per `skills/design/scripts/lib-phase-driver.md`). A tampered or malformed result env could assign multiline `VALIDATE_LOG_FILE` values into shell variables used for Fix-and-retry/Override UI. **Suggested fix:** Replace the inline loop with `phase_driver_read_result_env` (or equivalent awk extraction) for the documented allowlist, and add a structure pin requiring that helper at every merged rc `10` site.
- **Reviewer**: dyn-reentry-env-reads-output.txt
- **Concern**: - **architecture** `skills/design/SKILL.md:895-911` — The only merged fence with an executable allowlisted result-env read is initial Step 2b; Gate B and discussion-round2 rely on prose. The read uses a hand-rolled `while`/`printf -v` loop instead of `phase_driver_read_result_env` from `skills/design/scripts/lib-phase-driver.sh:66-91`, which is the repo’s normative allowlisted parser (symlink refusal plus multiline-value rejection per `skills/design/scripts/lib-phase-driver.md`). A tampered or malformed result env could assign multiline `VALIDATE_LOG_FILE` values into shell variables used for Fix-and-retry/Override UI. **Suggested fix:** Replace the inline loop with `phase_driver_read_result_env` (or equivalent awk extraction) for the documented allowlist, and add a structure pin requiring that helper at every merged rc `10` site.
- **Suggested revision**: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] Fix-and-retry re-entry is correctly centralized in `skills/design/SKILL.md:1549` (same-site `--with-plan-size` fence; raw emit/validate reserved for Step 5c).
- **Reviewer**: dyn-reentry-env-reads-output.txt
- **Concern**: - Fix-and-retry re-entry is correctly centralized in `skills/design/SKILL.md:1549` (same-site `--with-plan-size` fence; raw emit/validate reserved for Step 5c).
- **Suggested revision**: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] Override-after-rc10 routing to retained Step 2b.5 is documented for initial Step 2b (`skills/design/SKILL.md:939`), Gate B (`skills/design/references/approval-gates.md:158`), and discussion (`skills/design/references/discussion-rounds.md:126`).
- **Reviewer**: dyn-reentry-env-reads-output.txt
- **Concern**: - Override-after-rc10 routing to retained Step 2b.5 is documented for initial Step 2b (`skills/design/SKILL.md:939`), Gate B (`skills/design/references/approval-gates.md:158`), and discussion (`skills/design/references/discussion-rounds.md:126`).
- **Suggested revision**: Address the concern above.

### FINDING_42: [OUT_OF_SCOPE] No merged site reintroduces stdout KV merge heredocs (`<<<"${_postplan_out:-}"`); structure tests enforce absence in Gate B and discussion-round2.
- **Reviewer**: dyn-reentry-env-reads-output.txt
- **Concern**: - No merged site reintroduces stdout KV merge heredocs (`<<<"${_postplan_out:-}"`); structure tests enforce absence in Gate B and discussion-round2.
- **Suggested revision**: Address the concern above.

### FINDING_43: [OUT_OF_SCOPE] `design-postplan-emit.sh` rc `10` writes validator context to `.design-postplan-emit-result.env` before exit (`skills/design/scripts/design-postplan-emit.sh:521-525`); the gap is orchestrator-side reads at non–Step-2b sites, not driver emission.
- **Reviewer**: dyn-reentry-env-reads-output.txt
- **Concern**: - `design-postplan-emit.sh` rc `10` writes validator context to `.design-postplan-emit-result.env` before exit (`skills/design/scripts/design-postplan-emit.sh:521-525`); the gap is orchestrator-side reads at non–Step-2b sites, not driver emission.
- **Suggested revision**: Address the concern above.

