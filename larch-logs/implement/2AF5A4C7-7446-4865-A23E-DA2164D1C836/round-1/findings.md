### FINDING_1: code-quality: scripts/test-implement-rebase-macro.sh:170-190
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Harness sections (H) and (I) still require step8b_rebase and rebase-push.sh --no-push prose inside the retirement stub rebase-rebump-subprocedure.md make test-harnesses-13 fails on a clean tree after Phase 1 stubbing Update (H) to pin the live call site outside the stub; restrict (I) to conflict-resolution.md for still-valid tokens only
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/implement/references/conflict-resolution.md:5-117
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] conflict-resolution.md still mandates Re-bump Sub-procedure and /bump-version for step12_phase4 and step8b_rebase Merge-path orchestrator following this file hits a retirement stub and obsolete re-bump instructions Rewrite Phase 1 consumer contract; remove or historicalize dead caller_kind branches
- **Suggested revision**: Address the concern above.

### FINDING_3: risk-integration: scripts/launch-codex-ci.sh,scripts/launch-review.sh,scripts/lib-external-launcher-common.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] #3390 Codex quota mirroring is bundled with #3364 versioning removal Revert or debug of one concern affects unrelated launcher classification Split #3390 to its own PR or isolate commits in the PR description
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/ship-pr.sh:1050-1103,3258-3260
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Legacy phase id bump and run_bump_phase name after bump removal Operators and resume keys (RESUME_PHASE=bump) read as if versioning still runs Rename in a follow-up or document legacy id in ship-pr.md
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: python/rebase.py:285-303
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] rebase_and_rebump name persists though rebump logic was removed Phase 7 Python cutover readers assume bump still happens in this module Rename to rebase_and_push when editing python/ next
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: skills/implement/references/conflict-resolution.md:16
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Stale ship_pr_pre_push Phase 4 text still mandates classify/apply-bump after resume. Exit 5 conflict resolution completes; orchestrator follows doc and invokes removed bump machinery. Rewrite ship_pr_pre_push and step12/step8b sections for Phase 1 (resume ship-pr-rrr-phase14 only; no re-bump sub-procedure).
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/implement/SKILL.md:1036
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Exit 5 requires reading conflict-resolution.md which still describes removed bump flows. Same as above on any ship_pr_pre_push exit 5 during CI-fix rebase. Update conflict-resolution.md; optional explicit Phase 1 pointer in SKILL Exit 5 bullet.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/test-implement-rebase-macro.sh:170-190
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Harness still pins retired stub/sub-procedure strings; test exits 1 on this tree. make lint / relevant-checks fails invariant (H) despite plan claiming green harnesses. Update (H)/(I) pins for Phase 1 retirement stub and revised conflict-resolution.md.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/implement-finalize.sh:443-452
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Step 8b rebase conflicts stall (rebase-failed) instead of conflict-resolution handoff. Main moves during review; pre-PR rebase conflicts; run exits 4 with no automated conflict procedure. Confirm intent; either restore conflict handoff or document stall-only behavior in SKILL.md (fix line 951 overclaim).
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/ship-pr.sh:2673-2675
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] CI-fix run_rebase_rebump skips ship-branch-guard present in run_bump_phase. State BRANCH_NAME mismatch at CI rebase; wrong branch may be rebased/force-pushed. Relocate guard to post-rebase push path or accept and document in ship-pr.md.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/ship-pr.sh:1106-1107
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Dead STATUS=conflict arm in run_bump_phase after postbump contract change. No runtime effect; confuses readers and reviewers. Remove conflict arm or align postbump STATUS values with ship-pr case table.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] code-quality: scripts/check-bump-version.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] .bump-version-armed may still be written; hook no longer reads it. Orphan sentinel file in tmpdir only. Remove arming in Phase 5 when scripts are deleted.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/ship-pr.sh:1105-1110 + skills/implement/SKILL.md:1036
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Branch removes ship-pr.sh exit 5 (main had one postbump path); SKILL.md still documents Exit 5 orchestrator conflict-resolution. Step 8b rebase conflicts stall via exit 4 / exit_stall 8b instead of the documented Exit 5 + conflict-resolution.md handoff; orchestrator following SKILL may never run Phase 1-4 conflict resolution. Align SKILL exit matrix with actual exits; or restore exit 5 + CONFLICT_FILES where documented; add grep pin that ship-pr exit codes match SKILL.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/ship-pr.sh:1105-1107
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] run_bump_phase conflict status branch is dead code after implement-finalize stopped emitting STATUS=conflict. Future readers may think Exit 5 / conflict handoff still exists from this case arm. Remove conflict arm or restore real STATUS=conflict emission from implement-finalize.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/ship-pr.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Large ship-pr.sh deletion with no replacement integration harness after test-ship-pr removal (plan acknowledges). CI-fix rebase regression or accidental classify-bump/commit-changelog call could ship without failing make targets that still run. Add offline ship-pr phase harness for run_bump_phase/run_rebase_rebump or narrow acceptance to Python path + document bash gap until Phase 7.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: (plan acceptance)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No automated test for concurrency acceptance (second PR merges without rebase when disjoint). Keystone cost goal regresses silently if bump/CHANGELOG writes reappear on another path. Add manual repro doc or hermetic two-PR fixture; mark optional in CI.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/ship-pr.sh:2673-2675
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] run_rebase_rebump skips ship-branch-guard; only run_bump_phase enforces it. CI-fix rebase on wrong branch or detached HEAD may proceed further before detached-head check. Relocate shared guard into run_rebase_rebump entry or add harness for CI-fix branch alignment.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] risk-integration: scripts/test-implement-anti-halt.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Removed post-bump-version anti-halt pins without inert-hook replacement test. Hook regression could re-arm bump continuation without structural failure until runtime. Optional: pin hook-post-bump-version.sh early-exit in test-implement-structure.sh.
- **Suggested revision**: Address the concern above.

### FINDING_19: **No new injection surfaces** — removed code paths (`classify-bump.sh` / `apply-bump.sh` / `commit-changelog.sh`, rebump helpers, reasoning-file reads) shrink shell/git invocation driven by bump state; remaining paths keep existing validation (`resolve_checks_log_path`, `ship-pr-state.sh` never sourced).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No new injection surfaces** — removed code paths (`classify-bump.sh` / `apply-bump.sh` / `commit-changelog.sh`, rebump helpers, reasoning-file reads) shrink shell/git invocation driven by bump state; remaining paths keep existing validation (`resolve_checks_log_path`, `ship-pr-state.sh` never sourced).
- **Suggested revision**: Address the concern above.

### FINDING_20: **Branch safety preserved** — `bump-branch-guard` logic was relocated/renamed to `ship-branch-guard` inside `run_bump_phase` (empty branch, name mismatch, non-forked `main`/`master` stall).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Branch safety preserved** — `bump-branch-guard` logic was relocated/renamed to `ship-branch-guard` inside `run_bump_phase` (empty branch, name mismatch, non-forked `main`/`master` stall).
- **Suggested revision**: Address the concern above.

### FINDING_21: **Hooks reduced** — `hook-post-bump-version.sh` is an immediate no-op; `hook-stop-fail-close.sh` no longer arms `.bump-version-armed` / reads `postbump-state.sh` mid-ship.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Hooks reduced** — `hook-post-bump-version.sh` is an immediate no-op; `hook-stop-fail-close.sh` no longer arms `.bump-version-armed` / reads `postbump-state.sh` mid-ship.
- **Suggested revision**: Address the concern above.

### FINDING_22: **#3390 quota mirroring** — `external_launcher_mirror_quota_from_events` reuses `external_is_quota_failure` on a launcher-controlled `${OUTPUT}.events.jsonl`; appends a fixed-format marker with `%s` for the path (no format-string injection). Sidecar is local classification input only; intentional recall-biased regex per comments.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **#3390 quota mirroring** — `external_launcher_mirror_quota_from_events` reuses `external_is_quota_failure` on a launcher-controlled `${OUTPUT}.events.jsonl`; appends a fixed-format marker with `%s` for the path (no format-string injection). Sidecar is local classification input only; intentional recall-biased regex per comments.
- **Suggested revision**: Address the concern above.

### FINDING_23: **`--timing-task-kind` validation** in `launch-review.sh` (non-empty, non-flag-like) closes argv-smuggling mis-parsing (#1480 class) — defensive, not a regression.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`--timing-task-kind` validation** in `launch-review.sh` (non-empty, non-flag-like) closes argv-smuggling mis-parsing (#1480 class) — defensive, not a regression.
- **Suggested revision**: Address the concern above.

### FINDING_24: **No secrets introduced** in the reviewed code diff.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No secrets introduced** in the reviewed code diff. ---
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **risk-integration** `scripts/merge-pr.sh:360-406` — Pre-merge `version_already_published` only runs when `origin/main..HEAD` contains a `Bump version to X.Y.Z` commit. Phase 1 stops creating those commits, so the gate is effectively dormant until `/release` (Phase 3). **Why out of scope:** `merge-pr.sh` is not in the diff; this is an accepted, plan-documented trade-off, not a new code defect. **Suggested fix (process):** track Phase 3 `/release` + any merge-gate rework so version integrity does not rely on absent bump subjects.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **architecture** `skills/implement/references/conflict-resolution.md` — Still documents `caller_kind=step8b_rebase` and sub-procedure dispatch, while `rebase-rebump-subprocedure.md` is a retirement stub and `run_bump_phase` no longer emits Exit 5 / `step8b_rebase` handoff. **Why out of scope:** file not modified in this branch’s feature diff (stale cross-doc). **Risk:** orchestrator confusion / wrong recovery path, not a direct injection or auth bypass.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **correctness** `scripts/test-implement-rebase-macro.sh:180-185` — Still requires `step8b_rebase` prose inside the stubbed sub-procedure doc; the stub no longer contains those strings. **Why out of scope:** test harness only; unrelated to security boundaries. --- **Summary:** Phase 1 is a large, mostly deletion-driven change that removes hot-spot version/CHANGELOG mutations and associated state-machine complexity. I did not find injection, secret leakage, unsafe deserialization, or new trust-boundary violations introduced by the branch. The main **integrity** consideration is the intentional weakening of per-PR semver enforcement until `/release` lands — noted above as out-of-scope process debt, not an exploitable defect in this diff.
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: skills/implement/SKILL.md:1035-1036
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 8+ Exit 5 handler is dead while ship_pr_pre_push conflict handoff now exits 4 via exit_stall. After run_rebase_rebump sets RESUME_PHASE=ship-pr-rrr-phase14 and emits CONFLICT_FILES, orchestrator follows Exit 4 to Step 16 stall instead of conflict-resolution Phase 1-4; CI-fix rebase conflicts stall without resume. Restore exit 5 for this handoff only, or teach Exit 4 to branch on RESUME_PHASE/CALLER_KIND and run conflict-resolution before Step 16; sync ship-pr.md.
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: scripts/test-implement-rebase-macro.sh:170-190
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] test-implement-rebase-macro still requires retired rebase-rebump-subprocedure.md prose; test fails (H count=0, I grep miss). make lint / test-harnesses-13 fails on this branch despite acceptance criteria. Rewrite sections H and I for Phase 1 stub and current call sites (implement-finalize/ship-pr/conflict-resolution.md).
- **Suggested revision**: Address the concern above.

### FINDING_30: architecture: scripts/ship-pr.sh:2673-2675
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] run_rebase_rebump skips ship-branch-guard documented for run_bump_phase only. Wrong-branch or main/master checkout during CI-fix rebase may force-push or stall late without bump-phase guardrails. Share bump-branch-guard (or equivalent) before run_rebase_rebump rebase-push, or document as explicit accepted risk.
- **Suggested revision**: Address the concern above.

### FINDING_31: correctness: scripts/ship-pr.sh:1101-1110
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] run_bump_phase still handles postbump STATUS=conflict but postbump no longer returns it. Future maintainer may think conflict exit_stall 8b is live; debugging wrong branch. Remove or narrow the conflict case to match implement-finalize postbump statuses.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] architecture: skills/implement/references/conflict-resolution.md:3-112
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Stale exit-5 and re-bump/sub-procedure instructions not updated in Phase 1. Operator or agent loads conflict-resolution.md and follows obsolete ship_pr_pre_push / step8b_rebase paths. Update in a follow-up doc pass aligned with SKILL.md exit-code table (not modified in this diff).
- **Suggested revision**: Address the concern above.

### FINDING_33: correctness: skills/implement/references/conflict-resolution.md:5-117
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Full pre-Phase-1 conflict contract still mandates Rebase + Re-bump Sub-procedure and step8b/step12 re-bump paths while SKILL.md requires reading the entire file on Exit 5 and early_rebase conflicts. Orchestrator follows stale Phase 4 instructions (step12_phase4 / step8b_rebase) and attempts retired bump/re-bump after conflict resolution. Rewrite for Phase 1: only early_rebase and ship_pr_pre_push; retire dead caller_kind branches; align Step 12 with ship-pr.sh run_rebase_rebump.
- **Suggested revision**: Address the concern above.

### FINDING_34: architecture: docs/run-logs.md:339-343
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] version-bump-reasoning.md documented as written at Step 8 after version-bump phase. Post-Phase-1 runs omit the file; operators mis-audit runs or completeness expectations drift. Update run-logs contract for optional/historical batch or /release-only writes.
- **Suggested revision**: Address the concern above.

### FINDING_35: correctness: docs/skills.md:25
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] /alias docs still list version bump in /implement pipeline. Misleading operator/docs topology vs Phase 1 behavior. Remove version bump from /alias pipeline description; point to /release.
- **Suggested revision**: Address the concern above.

### FINDING_36: correctness: docs/linting.md:278
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Makefile doc row still describes old Step 8a changelog harness behavior. Contributors run make target expecting old semantics; drifts from repurposed test. Update linting.md and test-step-8a-changelog.md to negative-test contract.
- **Suggested revision**: Address the concern above.

### FINDING_37: architecture: skills/implement/scripts/hook-stop-fail-close.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Sibling doc still documents removed .bump-version-armed Stop-hook block. Operators trust md over sh and attempt obsolete Step-8 recovery. Strike bump section; document Phase 1 retirement.
- **Suggested revision**: Address the concern above.

### FINDING_38: correctness: .claude/skills/bump-version/SKILL.md:36-37
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] PATCH policy still says every PR must bump. Manual/release bump skill contradicts Phase 1 /implement path. Reword to release/operator-initiated bump policy.
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] risk-integration: scripts/launch-codex-ci.sh (branch)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] #3395 codex quota mirroring not in #3364 plan. Unrelated behavior in same PR. Split or accept as bundled fix; out of Phase 1 fidelity scope.
- **Suggested revision**: Address the concern above.

