### FINDING_1: code-quality: skills/implement/references/conflict-resolution.md:3-17,114-117
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Partial Phase 1 edit leaves contradictory step8b_rebase/step12_phase4 sub-procedure and fresh-bump instructions beside retirement notes Orchestrator loads conflict-resolution after ship-pr exit 4 or for Step 12 and follows Phase 4 bullets that mandate retired /bump-version sub-procedure dispatch Remove unreachable caller families; align Step 12 Phase 4 with ship-pr-only CI-fix rebase; scrub bump-sub-procedure assumptions in trivial-file notes
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/test-implement-rebase-macro.sh:192-194
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Harness still requires step8b_rebase dispatch pin in conflict-resolution.md Blocks coherent doc retirement and enforces unreachable contract text per plan Drop step8b_rebase pin; assert only ship_pr_pre_push and Phase 1 exit semantics
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/ship-pr.md:131
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] NEVER #11 cross-reference is stale after NEVER renumbering Maintainers follow wrong invariant (finalize-state vs bump breadcrumb) Point to issue #1944 / SKILL verbosity rule or add a dedicated NEVER for breadcrumb suppression
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/ship-pr.sh:1050-1114
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] run_bump_phase name and changelog-failed case no longer match behavior Readers misread state machine; dead status arm never taken from postbump Rename phase when convenient; prune changelog-failed from case list
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/ship-pr.sh:2673-2675
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] CI-fix rebase path skips ship-branch-guard documented at run_bump_phase CI-fix push from wrong branch if checkout/state diverge after pre-ship guard Share guard helper with run_rebase_rebump or document accepted risk in ship-pr.md
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: skills/implement/references/conflict-resolution.md:3-7,14-17,116-117
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Phase 1 retired the re-bump sub-procedure but conflict-resolution.md still tells the orchestrator Step 12/step8b Phase 4 must dispatch step12_phase4/step8b_rebase into that stub and run /bump-version. An orchestrator following conflict-resolution.md during a merge or ship stall loads dead instructions instead of ship_pr_pre_push + ship-pr-rrr-phase14 resume, causing wrong recovery or stall without re-entering ship-pr.sh. Rewrite Consumer/Contract/caller-family/Phase-4 Step 12 sections for Phase 1: only early_rebase and ship_pr_pre_push; remove or mark unreachable step12_phase4 and step8b_rebase; update test-implement-rebase-macro.sh pins accordingly.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/ship-pr.md:74,133 vs scripts/implement-finalize.sh:588
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] ship-pr.md documents postbump STATUS=conflict but implement-finalize emits STATUS=rebase-failed for rebase exit 1; run_bump_phase conflict branch may be dead. Operators or tooling expecting STATUS=conflict never see it; debugging postbump rebase failures is inconsistent with tests and implement-finalize.md. Align ship-pr.md with rebase-failed or restore conflict status everywhere; drop or document the unused conflict case in run_bump_phase.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/ship-pr.sh:2673-2675
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] run_rebase_rebump skips ship-branch-guard while run_bump_phase still enforces it. CI-fix rebase+force-push on a wrong or detached checkout can push to the wrong remote branch without the bump-phase guard firing. Relocate ship-branch-guard to run_rebase_rebump entry (and resume path) or document the accepted risk explicitly in ship-pr.md.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] risk-integration: (commits) d45f89d90
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] #3390 Codex quota classification changes are unrelated to versioning Phase 1. Increases review and regression scope for a versioning-focused PR. Split into a separate PR or call out clearly in the PR description.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/shared/subskill-invocation.md:59-73
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Canonical post-invocation verification still documents /bump-version plus check-bump-version pre/post and points to Step 8+ ship recipe. An /implement orchestrator loading shared SSOT may still run per-PR bump verification after ship-pr despite Phase 1 removal. Replace with a Phase-1-accurate example; mark bump path retired; add a docs-sync structural pin.
- **Suggested revision**: Address the concern above.

### FINDING_11: **`scripts/ship-pr.sh` / `scripts/implement-finalize.sh`**: Subtractive change removes `classify-bump.sh`, `apply-bump.sh`, `commit-changelog.sh`, and bump-reasoning file reads from the live ship path. That **shrinks** attack surface (fewer shell-outs and fewer session-state file reads). Removed `validate_bump_reasoning_file` (tmpdir containment, symlink rejection, size cap) is not a regression because `postbump` no longer reads `BUMP_REASONING_FILE` from disk.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`scripts/ship-pr.sh` / `scripts/implement-finalize.sh`**: Subtractive change removes `classify-bump.sh`, `apply-bump.sh`, `commit-changelog.sh`, and bump-reasoning file reads from the live ship path. That **shrinks** attack surface (fewer shell-outs and fewer session-state file reads). Removed `validate_bump_reasoning_file` (tmpdir containment, symlink rejection, size cap) is not a regression because `postbump` no longer reads `BUMP_REASONING_FILE` from disk.
- **Suggested revision**: Address the concern above.

### FINDING_12: **State files**: `ship-pr-state.sh` / `postbump-state.sh` remain parse-only (`awk` / `read_state`); they are not `source`d. argv validation for CR/LF in `--manifest-path` / `--run-id` is unchanged.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **State files**: `ship-pr-state.sh` / `postbump-state.sh` remain parse-only (`awk` / `read_state`); they are not `source`d. argv validation for CR/LF in `--manifest-path` / `--run-id` is unchanged.
- **Suggested revision**: Address the concern above.

### FINDING_13: **`external_launcher_mirror_quota_from_events`** (#3395): Appends a **fixed-format** marker line; only the events **path** is interpolated (quoted `%s`). Quota detection reuses `external_is_quota_failure` on the JSONL stream—no `eval`, no command substitution. Fail-closed quota classification is intentional; false positives degrade to waterfall, not privilege gain.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`external_launcher_mirror_quota_from_events`** (#3395): Appends a **fixed-format** marker line; only the events **path** is interpolated (quoted `%s`). Quota detection reuses `external_is_quota_failure` on the JSONL stream—no `eval`, no command substitution. Fail-closed quota classification is intentional; false positives degrade to waterfall, not privilege gain.
- **Suggested revision**: Address the concern above.

### FINDING_14: **`launch-review.sh`**: Quota mirroring runs **inside** the transient-retry loop **before** `external_is_transient_infra_failure`, with an explicit `! external_is_quota_failure` guard—reduces quota burn, not a trust-boundary weakening.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`launch-review.sh`**: Quota mirroring runs **inside** the transient-retry loop **before** `external_is_transient_infra_failure`, with an explicit `! external_is_quota_failure` guard—reduces quota burn, not a trust-boundary weakening.
- **Suggested revision**: Address the concern above.

### FINDING_15: **Hooks**: `hook-post-bump-version.sh` is an immediate `exit 0` no-op; `hook-stop-fail-close.sh` drops the `.bump-version-armed` block only because that sentinel is never written post–Phase 1. Remaining Stop-hook still blocks mid–Step 5.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Hooks**: `hook-post-bump-version.sh` is an immediate `exit 0` no-op; `hook-stop-fail-close.sh` drops the `.bump-version-armed` block only because that sentinel is never written post–Phase 1. Remaining Stop-hook still blocks mid–Step 5.
- **Suggested revision**: Address the concern above.

### FINDING_16: **`python/rebase.py`**: Re-bump/changelog limbs removed; CI-fix path keeps fetch/rebase/`_resolve_conflicts`/force-push. No new deserialization or network fetch from untrusted input.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`python/rebase.py`**: Re-bump/changelog limbs removed; CI-fix path keeps fetch/rebase/`_resolve_conflicts`/force-push. No new deserialization or network fetch from untrusted input.
- **Suggested revision**: Address the concern above.

### FINDING_17: **Secrets**: No new credentials, tokens, or literal secret material in production paths (test-only `CURSOR_API_KEY="sl-quota-cursor-key"` in harness fixtures is clearly dummy).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Secrets**: No new credentials, tokens, or literal secret material in production paths (test-only `CURSOR_API_KEY="sl-quota-cursor-key"` in harness fixtures is clearly dummy).
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **risk-integration** `scripts/ship-pr.sh` — `run_rebase_rebump` still does **not** run `ship-branch-guard` before rebase/force-push (documented in the updated comment: relies on correct checkout + state alignment). `git-force-push.sh` pushes **current** `HEAD` branch, not `read_state BRANCH_NAME`. A desynced checkout could force-push the wrong branch during CI-fix; this predates Phase 1 and is not introduced by the bump removal, but the Phase 1 edit makes the omission more visible. **Suggested fix:** (if desired later) call the same branch-alignment check at `run_rebase_rebump` entry as in `run_bump_phase`.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `scripts/lib-external-launcher-common.sh` — `external_is_quota_failure` / `external_launcher_mirror_quota_from_events` classify quota via **substring** grep over the full Codex JSONL events file. Benign JSON prose containing tokens like `"quota"` could false-positive (fail-closed by design). Not a confidentiality issue; at worst mis-routes the external panel. **Suggested fix:** none required unless false-positive rate matters; optional structured parse of `type":"error"` events instead of line grep.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/ship-pr.md:74,133; scripts/ship-pr.sh:1106-1107
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Postbump conflict documented as STATUS=conflict but implement-finalize emits STATUS=rebase-failed; conflict case is dead code Operator or agent reads ship-pr.md, expects conflict handoff, but run_bump_phase only sees rebase-failed and exit_stall 8b with no conflict branch executed Align ship-pr.md and run_bump_phase case arms with rebase-failed; remove dead conflict) branch or restore STATUS=conflict emission if handoff is intended
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: skills/implement/references/conflict-resolution.md:3-7,14-17,114-117
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Phase 1 retirement notes conflict with live step8b_rebase and Step 12 bullets that still mandate Rebase+Re-bump Sub-procedure and /bump-version Operator or orchestrator loading conflict-resolution during ship_pr_pre_push or Step 12 conflict may invoke retired sub-procedure and per-PR bump contrary to Phase 1 Rewrite or remove step8b_rebase and step12_phase4 families and Step 12 Phase 4 exit-0 text; align test-implement-rebase-macro (I) pins
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: docs/skills.md:25
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Alias docs still claim /implement performs version bump Users routing via /alias expect automatic per-PR bump on implement runs Update line to Phase 1 ship contract (review+PR; bump via /release not /implement)
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: docs/review-agents.md:89
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Review-agents doc still lists version-bump reasoning as /implement run-log content Readers assume implement merges always carry bump reasoning batches Remove or qualify version-bump reasoning for implement; point to /release
- **Suggested revision**: Address the concern above.

### FINDING_24: architecture: docs/run-logs.md:3,343,383
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Run-log docs still document version-bump batches and pre-bump transcript cut at version bump Operators misread merged larch-logs and token reports after Phase 1 Update run-logs.md for no implement ship-path bump; fix transcript boundary wording
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: scripts/ship-pr.md:131
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] NEVER #11 cross-reference no longer matches renumbered SKILL.md rule for ship-pr breadcrumbs Maintainers follow wrong NEVER rule when editing ship-pr.md Fix xref to current anti-halt/breadcrumb guidance in SKILL.md
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] architecture: scripts/test-implement-rebase-macro.sh:192-194
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Harness requires step8b_rebase token in conflict-resolution.md Blocks full retirement of dead caller_kind prose in conflict-resolution Revisit pin after conflict-resolution.md cleanup (not in Phase 1 plan file list)
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] risk-integration: branch commit d45f89d90
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Unrelated Codex usage-limit changes bundled on same branch Reviewers must separate #3395 from #3364 acceptance Treat as separate concern in PR review
- **Suggested revision**: Address the concern above.

### FINDING_28: **correctness** `scripts/implement-finalize.sh:560` — On the corrupt-checkpoint path, `postbump_tail` hard-codes `CHANGELOG_STATUS=skipped-resume` instead of `skipped-phase1`. Every other Phase 1 path (including `postbump-cwd-not-repo` at 548/553 and the `force-push-gate` resume arm at 565) uses `skipped-phase1` for changelog; only this fail-closed branch diverges from `scripts/implement-finalize.md:57-60`, which documents `CHANGELOG_STATUS=skipped-phase1|skipped-resume` with `skipped-phase1` as the Phase 1 default. `ship-pr.sh` keys off `STATUS`, so behavior is unchanged, but run-log / audit consumers that parse `CHANGELOG_STATUS` can misread a corrupt checkpoint as a resume skip. **Suggested fix:** Pass `skipped-phase1` as the third argument (or reuse `$CHANGELOG_STATUS` after setting it to `skipped-phase1` before the tail), e.g. `postbump_tail postbump-state-corrupt skipped skipped-phase1 skipped-resume absent`.
- **Reviewer**: dyn-script-state-machine-output.txt
- **Concern**: - **correctness** `scripts/implement-finalize.sh:560` — On the corrupt-checkpoint path, `postbump_tail` hard-codes `CHANGELOG_STATUS=skipped-resume` instead of `skipped-phase1`. Every other Phase 1 path (including `postbump-cwd-not-repo` at 548/553 and the `force-push-gate` resume arm at 565) uses `skipped-phase1` for changelog; only this fail-closed branch diverges from `scripts/implement-finalize.md:57-60`, which documents `CHANGELOG_STATUS=skipped-phase1|skipped-resume` with `skipped-phase1` as the Phase 1 default. `ship-pr.sh` keys off `STATUS`, so behavior is unchanged, but run-log / audit consumers that parse `CHANGELOG_STATUS` can misread a corrupt checkpoint as a resume skip. **Suggested fix:** Pass `skipped-phase1` as the third argument (or reuse `$CHANGELOG_STATUS` after setting it to `skipped-phase1` before the tail), e.g. `postbump_tail postbump-state-corrupt skipped skipped-phase1 skipped-resume absent`.
- **Suggested revision**: Address the concern above.

### FINDING_29: **risk-integration** `scripts/ship-pr.sh:1101-1114` — `run_bump_phase` still branches on `STATUS=conflict` and `changelog-failed`, but Phase 1 `implement-finalize.sh` no longer emits either: rebase exit 1 now returns `STATUS=rebase-failed` without writing `.postbump-phase` or `RESUME_PHASE`/`CALLER_KIND` (see `run_step8b_rebase` 443-452 and `run_postbump` 588; diff removes the old `STATUS=conflict` + checkpoint handoff). The producer/consumer contract is therefore incomplete—those arms are dead on the normal path, and a mixed-version or hand-crafted `STATUS=conflict` line would stall at `8b` via `exit_stall` instead of the removed exit-5 / sub-procedure path, with no `RESUME_PHASE` on stdout. **Suggested fix:** Drop the `conflict)` arm and `changelog-failed` from the `case` (or map them explicitly to the same handling as `rebase-failed`), and align `scripts/ship-pr.md` with the documented `STATUS=` set in `scripts/implement-finalize.md:60`.
- **Reviewer**: dyn-script-state-machine-output.txt
- **Concern**: - **risk-integration** `scripts/ship-pr.sh:1101-1114` — `run_bump_phase` still branches on `STATUS=conflict` and `changelog-failed`, but Phase 1 `implement-finalize.sh` no longer emits either: rebase exit 1 now returns `STATUS=rebase-failed` without writing `.postbump-phase` or `RESUME_PHASE`/`CALLER_KIND` (see `run_step8b_rebase` 443-452 and `run_postbump` 588; diff removes the old `STATUS=conflict` + checkpoint handoff). The producer/consumer contract is therefore incomplete—those arms are dead on the normal path, and a mixed-version or hand-crafted `STATUS=conflict` line would stall at `8b` via `exit_stall` instead of the removed exit-5 / sub-procedure path, with no `RESUME_PHASE` on stdout. **Suggested fix:** Drop the `conflict)` arm and `changelog-failed` from the `case` (or map them explicitly to the same handling as `rebase-failed`), and align `scripts/ship-pr.md` with the documented `STATUS=` set in `scripts/implement-finalize.md:60`.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-script-state-machine-output.txt
- **Concern**: - **correctness** `skills/implement/references/conflict-resolution.md:114` — Phase 4 still documents `caller_kind=step8b_rebase` and mandates invoking the retired `rebase-rebump-subprocedure.md`. Postbump conflicts no longer reach that handoff; an orchestrator following this paragraph could still attempt a re-bump sub-procedure that Phase 1 removed. Worth a doc sync in a follow-up, not an `implement-finalize.sh` state-machine defect.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-script-state-machine-output.txt
- **Concern**: - **code-quality** `scripts/test-implement-finalize.sh` — Harness asserts `CHANGELOG_STATUS=skipped-phase1` on happy, checkpoint, and conflict paths but not on the `postbump-state-corrupt` path (975), so the line 560 regression would not be caught by CI. **Commits reviewed (since merge-base with main):** `d45f89d90` … `bf25470bb` (Phase 1 #3364 plus review/checks follow-ups). **Summary:** No live `read_state('HAS_BUMP')` remains in `implement-finalize.sh`; `postbump_tail` call sites all use the five-argument shape consistently; `CHANGELOG_STATUS` is only `skipped-phase1` or `skipped-resume` at runtime (never legacy `updated` / `skipped-no-bump` / `changelog-failed`); stale `HAS_BUMP=true` in `postbump-state.sh` is tolerated because the key is no longer required. The state machine is coherent for the main path; the items above are telemetry/consumer drift, not ship-blocking logic errors.
- **Suggested revision**: Address the concern above.

