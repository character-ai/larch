### FINDING_1: code-quality: skills/implement/references/conflict-resolution.md:3-17,114-117
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Partial Phase 1 edit leaves contradictory step8b_rebase/step12_phase4 sub-procedure and fresh-bump instructions beside retirement notes Orchestrator loads conflict-resolution after ship-pr exit 4 or for Step 12 and follows Phase 4 bullets that mandate retired /bump-version sub-procedure dispatch Remove unreachable caller families; align Step 12 Phase 4 with ship-pr-only CI-fix rebase; scrub bump-sub-procedure assumptions in trivial-file notes
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: scripts/test-implement-rebase-macro.sh:192-194
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Harness still requires step8b_rebase dispatch pin in conflict-resolution.md Blocks coherent doc retirement and enforces unreachable contract text per plan Drop step8b_rebase pin; assert only ship_pr_pre_push and Phase 1 exit semantics
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: scripts/ship-pr.md:74,133; scripts/ship-pr.sh:1106-1107
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Postbump conflict documented as STATUS=conflict but implement-finalize emits STATUS=rebase-failed; conflict case is dead code Operator or agent reads ship-pr.md, expects conflict handoff, but run_bump_phase only sees rebase-failed and exit_stall 8b with no conflict branch executed Align ship-pr.md and run_bump_phase case arms with rebase-failed; remove dead conflict) branch or restore STATUS=conflict emission if handoff is intended
- **Suggested revision**: Address the concern above.


### FINDING_21: correctness: skills/implement/references/conflict-resolution.md:3-7,14-17,114-117
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Phase 1 retirement notes conflict with live step8b_rebase and Step 12 bullets that still mandate Rebase+Re-bump Sub-procedure and /bump-version Operator or orchestrator loading conflict-resolution during ship_pr_pre_push or Step 12 conflict may invoke retired sub-procedure and per-PR bump contrary to Phase 1 Rewrite or remove step8b_rebase and step12_phase4 families and Step 12 Phase 4 exit-0 text; align test-implement-rebase-macro (I) pins
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: scripts/ship-pr.md:131
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] NEVER #11 cross-reference no longer matches renumbered SKILL.md rule for ship-pr breadcrumbs Maintainers follow wrong NEVER rule when editing ship-pr.md Fix xref to current anti-halt/breadcrumb guidance in SKILL.md
- **Suggested revision**: Address the concern above.


### FINDING_28: **correctness** `scripts/implement-finalize.sh:560` — On the corrupt-checkpoint path, `postbump_tail` hard-codes `CHANGELOG_STATUS=skipped-resume` instead of `skipped-phase1`. Every other Phase 1 path (including `postbump-cwd-not-repo` at 548/553 and the `force-push-gate` resume arm at 565) uses `skipped-phase1` for changelog; only this fail-closed branch diverges from `scripts/implement-finalize.md:57-60`, which documents `CHANGELOG_STATUS=skipped-phase1|skipped-resume` with `skipped-phase1` as the Phase 1 default. `ship-pr.sh` keys off `STATUS`, so behavior is unchanged, but run-log / audit consumers that parse `CHANGELOG_STATUS` can misread a corrupt checkpoint as a resume skip. **Suggested fix:** Pass `skipped-phase1` as the third argument (or reuse `$CHANGELOG_STATUS` after setting it to `skipped-phase1` before the tail), e.g. `postbump_tail postbump-state-corrupt skipped skipped-phase1 skipped-resume absent`.
- **Reviewer**: dyn-script-state-machine-output.txt
- **Concern**: - **correctness** `scripts/implement-finalize.sh:560` — On the corrupt-checkpoint path, `postbump_tail` hard-codes `CHANGELOG_STATUS=skipped-resume` instead of `skipped-phase1`. Every other Phase 1 path (including `postbump-cwd-not-repo` at 548/553 and the `force-push-gate` resume arm at 565) uses `skipped-phase1` for changelog; only this fail-closed branch diverges from `scripts/implement-finalize.md:57-60`, which documents `CHANGELOG_STATUS=skipped-phase1|skipped-resume` with `skipped-phase1` as the Phase 1 default. `ship-pr.sh` keys off `STATUS`, so behavior is unchanged, but run-log / audit consumers that parse `CHANGELOG_STATUS` can misread a corrupt checkpoint as a resume skip. **Suggested fix:** Pass `skipped-phase1` as the third argument (or reuse `$CHANGELOG_STATUS` after setting it to `skipped-phase1` before the tail), e.g. `postbump_tail postbump-state-corrupt skipped skipped-phase1 skipped-resume absent`.
- **Suggested revision**: Address the concern above.


### FINDING_29: **risk-integration** `scripts/ship-pr.sh:1101-1114` — `run_bump_phase` still branches on `STATUS=conflict` and `changelog-failed`, but Phase 1 `implement-finalize.sh` no longer emits either: rebase exit 1 now returns `STATUS=rebase-failed` without writing `.postbump-phase` or `RESUME_PHASE`/`CALLER_KIND` (see `run_step8b_rebase` 443-452 and `run_postbump` 588; diff removes the old `STATUS=conflict` + checkpoint handoff). The producer/consumer contract is therefore incomplete—those arms are dead on the normal path, and a mixed-version or hand-crafted `STATUS=conflict` line would stall at `8b` via `exit_stall` instead of the removed exit-5 / sub-procedure path, with no `RESUME_PHASE` on stdout. **Suggested fix:** Drop the `conflict)` arm and `changelog-failed` from the `case` (or map them explicitly to the same handling as `rebase-failed`), and align `scripts/ship-pr.md` with the documented `STATUS=` set in `scripts/implement-finalize.md:60`.
- **Reviewer**: dyn-script-state-machine-output.txt
- **Concern**: - **risk-integration** `scripts/ship-pr.sh:1101-1114` — `run_bump_phase` still branches on `STATUS=conflict` and `changelog-failed`, but Phase 1 `implement-finalize.sh` no longer emits either: rebase exit 1 now returns `STATUS=rebase-failed` without writing `.postbump-phase` or `RESUME_PHASE`/`CALLER_KIND` (see `run_step8b_rebase` 443-452 and `run_postbump` 588; diff removes the old `STATUS=conflict` + checkpoint handoff). The producer/consumer contract is therefore incomplete—those arms are dead on the normal path, and a mixed-version or hand-crafted `STATUS=conflict` line would stall at `8b` via `exit_stall` instead of the removed exit-5 / sub-procedure path, with no `RESUME_PHASE` on stdout. **Suggested fix:** Drop the `conflict)` arm and `changelog-failed` from the `case` (or map them explicitly to the same handling as `rebase-failed`), and align `scripts/ship-pr.md` with the documented `STATUS=` set in `scripts/implement-finalize.md:60`.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: scripts/ship-pr.md:131
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] NEVER #11 cross-reference is stale after NEVER renumbering Maintainers follow wrong invariant (finalize-state vs bump breadcrumb) Point to issue #1944 / SKILL verbosity rule or add a dedicated NEVER for breadcrumb suppression
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: skills/implement/references/conflict-resolution.md:3-7,14-17,116-117
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Phase 1 retired the re-bump sub-procedure but conflict-resolution.md still tells the orchestrator Step 12/step8b Phase 4 must dispatch step12_phase4/step8b_rebase into that stub and run /bump-version. An orchestrator following conflict-resolution.md during a merge or ship stall loads dead instructions instead of ship_pr_pre_push + ship-pr-rrr-phase14 resume, causing wrong recovery or stall without re-entering ship-pr.sh. Rewrite Consumer/Contract/caller-family/Phase-4 Step 12 sections for Phase 1: only early_rebase and ship_pr_pre_push; remove or mark unreachable step12_phase4 and step8b_rebase; update test-implement-rebase-macro.sh pins accordingly.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: scripts/ship-pr.md:74,133 vs scripts/implement-finalize.sh:588
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] ship-pr.md documents postbump STATUS=conflict but implement-finalize emits STATUS=rebase-failed for rebase exit 1; run_bump_phase conflict branch may be dead. Operators or tooling expecting STATUS=conflict never see it; debugging postbump rebase failures is inconsistent with tests and implement-finalize.md. Align ship-pr.md with rebase-failed or restore conflict status everywhere; drop or document the unused conflict case in run_bump_phase.
- **Suggested revision**: Address the concern above.


