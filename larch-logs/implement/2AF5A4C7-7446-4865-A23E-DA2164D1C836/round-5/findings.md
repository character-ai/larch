### FINDING_1: code-quality: scripts/ship-pr.sh:2645-2655
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicate defer_push if/else arms set identical state after re-bump removal Future edit to one branch only leaves the other stale and confuses reviewers during CI-fix work Collapse to one state_set_many after force-push
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: (commits d45f89d90 vs d37ec4e86)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] #3390 launcher quota mirroring bundled with #3364 versioning PR Revert/bisect of versioning work also reverts or conflicts with unrelated Codex classifier fix; review surface mixes two features Split #3390 to its own PR or document explicit batching decision
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/ship-pr.sh:3245-3266
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Retired --resume-phase values not accepted at CLI entry Operator or automation resumes with --resume-phase step8b_rebase after plugin upgrade; ship-pr dies before clearing stale state Map retired tokens to bump with warning or no-op clear per plan stale-key tolerance
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/ship-pr.sh,skills/implement/references/rebase-rebump-subprocedure.md:1
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Misleading re-bump/bump naming on rebase-only paths Operators grep for rebump and land in dead mental model or wrong docs Rename symbols or add legacy-phase-id comments at entry points
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/implement-finalize.sh:2
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale file header says post-bump Docs and new contributors assume version bump still runs in finalize Update header to post-ship / Step 8b wording
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/implement-finalize.sh:354-373
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Dead force-push-gate checkpoint reader after writer removal Harder to see actual postbump control flow; false sense resume still exists Remove or simplify checkpoint machinery
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: skills/implement/SKILL.md:34,50,56
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] NEVER tombstone entries for removed rules Longer NEVER list without adding enforcement Pre-existing style; optional cleanup in a docs-only follow-up
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: Makefile:564-565
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Makefile registers test-ship-pr-rebase in test-harnesses-13 but scripts/test-ship-pr-rebase.sh is not committed to the branch. make lint / test-harnesses-13 fails on clean checkout with missing script path. Commit scripts/test-ship-pr-rebase.sh or remove Makefile target until the harness is ready.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/implement-finalize.sh:405-448
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Postbump Step 8b rebase uses rebase-push --no-push without --keep-on-conflict; conflicts hard-stall at STALL_STEP=8b with no CONFLICT_FILES handoff. Branch behind main with overlapping non-bump file hits rebase conflict during postbump; run stalls with no automated conflict-resolution path. Wire keep-on-conflict handoff for postbump 8b or add harness pinning documented hard-stall contract.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/ci-decide.sh:134-146
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Phase 1 removes re-bump but ci-decide still emits ACTION=rebase when BEHIND_COUNT>0 and ship-pr still calls run_rebase_rebump. After concurrent PR merge B may still rebase in merge loop (without rebump), conflicting with strict no-rebase acceptance wording. Clarify Phase 1 acceptance as no-rebump only or implement merge-while-behind in Phase 2.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: Makefile:160 / agent-lint.toml:1020 / scripts/test-ship-pr-rebase.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Makefile shard 13 and agent-lint reference test-ship-pr-rebase.sh but the script is not committed on the branch. CI clone runs make test-harnesses-13 and fails because scripts/test-ship-pr-rebase.sh is missing. Commit scripts/test-ship-pr-rebase.sh (and contract doc) or remove Makefile/agent-lint entries until present.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: plan acceptance / scripts/ship-pr.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No harness automates the plan acceptance concurrency case (two disjoint PRs; second merges without rebase/re-bump). Regression restoring per-PR bump/CHANGELOG or unnecessary CI rebase can ship while make lint and listed harnesses stay green. Add a dual-branch offline harness or demote the acceptance item to documented manual-only verification.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/ship-pr.sh:2658-2912 / scripts/test-ship-pr-rebase.sh:19-44
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] run_rebase_rebump CI-fix path lacks sandbox integration tests; coverage is mostly grep plus one die_usage guard. Typo in defer-push wiring or phase-14 resume branch breaks production CI-fix rebase while rebase-push unit tests pass. Add stubbed-git cases in test-ship-pr-rebase.sh for defer-push invocation and resume handoff success.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/ship-pr.sh:1086-1094 / scripts/ship-pr.sh:3245-3266
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Stale RESUME_PHASE tokens are cleared on bump entry but unknown --resume-phase step8b_rebase still aborts. Mid-upgrade resume with legacy --resume-phase step8b_rebase dies with unknown resume-phase. Harness stale-state tolerance; optionally alias legacy resume tokens in the resume-phase case arm.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/test-implement-finalize.sh:947-949 / skills/implement/SKILL.md:85
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Postbump rebase conflicts no longer hand off to conflict-resolution.md; tests lock in manual recovery. First postbump rebase conflict after upgrade stalls without automated Phase 1-4 recovery. Document operator-facing degradation; re-wire only if a follow-up phase intends automated postbump recovery.
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/launch-codex-ci.sh:92-96` — Pre-existing pattern: when `--plan-file` is set, the full plan is embedded in the Codex CI-fix prompt via unbounded `$(cat "$PLAN_FILE")`. Plan text is treated as trusted in the launcher contract, but a hostile or compromised plan file is still prompt-injection surface for the external agent. Not introduced by this branch; unchanged in the diff hunk around the prompt build.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **architecture** `scripts/ship-pr.sh:1072-1077`, `scripts/implement-finalize.sh:313-318` — Pre-existing trust model, now mirrored in postbump validation: `FORKED_TARGET=true` allows `BRANCH_NAME=main|master` through branch guards and into rebase/force-push. `FORKED_TARGET` is a boolean in session state under `$IMPLEMENT_TMPDIR`, documented as an operator/runbook trust signal with no cryptographic fork proof. Same-UID tmpdir tampering could theoretically steer a push; that is the repo’s stated session trust model (`SECURITY.md` / `ship-pr.md`), not a new class of bug from Phase 1.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **risk-integration** `SECURITY.md` — The implementation plan lists `SECURITY.md` among docs to update when finalize/ship contracts change; this branch updates `implement-finalize.md` references but does not appear to revise `SECURITY.md` for retired bump-reasoning publication or postbump checkpoint semantics. Documentation drift only; no runtime exposure change.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/ship-pr.sh:3245-3266
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Legacy --resume-phase step8b_rebase and step8_apply_bump_same_version hit die_usage unknown --resume-phase; only in-state RESUME_PHASE is cleared when entering run_bump_phase. Operator or automation resumes a pre-Phase-1 interrupted run with ship-pr.sh --resume-phase step8b_rebase after upgrading larch; ship-pr exits 2 before the state machine advances, leaving PHASE stuck and requiring manual state surgery. Add case arms mapping step8b_rebase|step8_apply_bump_same_version|bump to advance_phase bump (and clear stale CALLER_KIND), matching force-push-gate tolerance; pin with test-ship-pr-rebase.sh.
- **Suggested revision**: Address the concern above.

### FINDING_20: architecture: scripts/implement-finalize.sh:405-448
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Postbump Step 8b rebase conflicts return rebase-failed and stall at 8b without CONFLICT_FILES or conflict-resolution.md, unlike CI-fix run_rebase_rebump. Feature branch is behind origin/main with conflicts in non-version files at pre-PR ship; implement-finalize aborts rebase, ship-pr exit_stall 8b, and the run stalls with no automated Phase 1-4 recovery despite CI-fix rebases still having that path. Document loudly in stall copy, or align postbump with --keep-on-conflict plus ship_pr_pre_push handoff if product wants parity (SKILL.md already notes accepted degradation).
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: scripts/ship-pr.md:128
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Invariants claim REBASE_COUNT >= 5 but run_rebase_rebump enforces 20. Operator reads ship-pr.md invariants and expects stall after five rebases while the run continues rebasing until twenty, confusing retry-storm diagnosis. Update the invariant bullet to >= 20 or point to the code constant.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] risk-integration: scripts/launch-codex-ci.sh:3291-3298
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Codex quota signal mirrored from events JSONL to sidecar on failure (#3390). If events file is missing on failure, classification may still fall back to generic non-auth (pre-existing launcher edge). Ensure external_launcher_mirror_quota_from_events is fail-open when events path absent; already likely fine for this branch.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: skills/shared/subskill-invocation.md:23
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Pattern B still lists /bump-version as a nested /implement child call after Phase 1 removed it. Contributors follow subskill-invocation.md and reintroduce /bump-version Skill calls from /implement. Update the Pattern B parenthetical to /review and /issue only, or add an explicit Phase 1 note that implement no longer nests bump-version.
- **Suggested revision**: Address the concern above.

### FINDING_24: architecture: scripts/implement-finalize.md:3
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Header still says Step 8 post-bump work though Phase 1 body describes rebase+push only. Operators assume postbump still performs version bump work. Rename header prose to post-ship/postbump (8b rebase + force-push) without post-bump wording.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: python/rebase.py:12
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan said drop import changelog; file still imports changelog for conflict auto_resolve. Plan auditors or Phase 7 cutover may treat Python mirror as incomplete. Clarify plan or module docstring that changelog import is conflict-resolution-only, not re-bump.
- **Suggested revision**: Address the concern above.

### FINDING_26: architecture: scripts/ship-pr.sh:3279-3281
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Dead CALLER_KIND branch step10_rebase_then_evaluate with no writer after rebump removal. Future maintainers think evaluate-failure routing differs for step10 rebase paths. Remove dead case arm or document and restore a writer if still needed.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] architecture: docs/linting.md:251
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Linting harness row still points to rebase-rebump-subprocedure.md for ci-wait synchronous-only rule; file is a retirement stub. Readers follow stale cross-ref and miss real ci-wait.md / SKILL.md guidance. Update linting.md and ci-wait.md site registry to current authorities (pre-existing drift amplified by stubbing).
- **Suggested revision**: Address the concern above.

### FINDING_28: **architecture** `scripts/ship-pr.sh:3245-3266` — Phase 1 only tolerates legacy `--resume-phase` values `force-push-gate` and `bump` (both route to `advance_phase bump`). Retired tokens `step8b_rebase` and `step8_apply_bump_same_version` are cleared from state only when `run_bump_phase` runs (`_clear_phase1_postbump_residue` at `1086-1095`), but if anything re-invokes `ship-pr.sh` with `--resume-phase step8b_rebase` or `--resume-phase step8_apply_bump_same_version` (stale automation, manual retry, or an orchestrator that copies persisted `RESUME_PHASE` into argv), the startup `case` hits the default arm and `die_usage "unknown --resume-phase"` exits **2** instead of degrading to the no-op bump path. That is weaker than the plan’s “tolerate-and-ignore” edge case for pre-Phase-1 state. **Suggested fix:** Extend the `3246` resume `case` to treat `step8b_rebase|step8_apply_bump_same_version|force-push-gate` like `bump` (advance to bump, clear `RESUME_PHASE`/`CALLER_KIND`, optionally log a one-line legacy-resume notice), and add a `test-ship-pr-rebase.sh` runtime case that seeds a pre-Phase-1 `ship-pr-state.sh` and asserts `--resume-phase step8b_rebase` does not exit 2.
- **Reviewer**: dyn-resume-compat-output.txt
- **Concern**: - **architecture** `scripts/ship-pr.sh:3245-3266` — Phase 1 only tolerates legacy `--resume-phase` values `force-push-gate` and `bump` (both route to `advance_phase bump`). Retired tokens `step8b_rebase` and `step8_apply_bump_same_version` are cleared from state only when `run_bump_phase` runs (`_clear_phase1_postbump_residue` at `1086-1095`), but if anything re-invokes `ship-pr.sh` with `--resume-phase step8b_rebase` or `--resume-phase step8_apply_bump_same_version` (stale automation, manual retry, or an orchestrator that copies persisted `RESUME_PHASE` into argv), the startup `case` hits the default arm and `die_usage "unknown --resume-phase"` exits **2** instead of degrading to the no-op bump path. That is weaker than the plan’s “tolerate-and-ignore” edge case for pre-Phase-1 state. **Suggested fix:** Extend the `3246` resume `case` to treat `step8b_rebase|step8_apply_bump_same_version|force-push-gate` like `bump` (advance to bump, clear `RESUME_PHASE`/`CALLER_KIND`, optionally log a one-line legacy-resume notice), and add a `test-ship-pr-rebase.sh` runtime case that seeds a pre-Phase-1 `ship-pr-state.sh` and asserts `--resume-phase step8b_rebase` does not exit 2.
- **Suggested revision**: Address the concern above.

### FINDING_29: **architecture** `scripts/ship-pr.sh:3213-3268` — `write_initial_state` and `require_key` were pruned consistently (`HAS_BUMP` / `BUMP_TYPE` / `NEW_VERSION` removed from `ship-pr-state.sh`; stubs live only in `write_postbump_state` → `postbump-state.sh` at `809-826`), and there are no unset `$HAS_BUMP` references under `set -u`. However, legacy keys left **inside** an existing `ship-pr-state.sh` are never stripped at load: extra keys are harmless, but stale `RESUME_PHASE` / `CALLER_KIND` can remain until bump entry or a successful `run_rebase_rebump` clear (`2684`), so a mid-CI stall can still expose `RESUME_PHASE=force-push-gate` + `CALLER_KIND=step8b_rebase` to the orchestrator even though Exit 5 / sub-procedure routing is gone. **Suggested fix:** After `validate_state_syntax` / `_ci_fix_pending_hydrate`, normalize legacy resume metadata once (mirror `_clear_phase1_postbump_residue`: blank `RESUME_PHASE`/`CALLER_KIND` when values are in the retired set, or when `PHASE` is not `bump` and `RESUME_PHASE` is not `ship-pr-rrr-phase14`), so persisted state cannot contradict Phase 1 semantics across CI phases.
- **Reviewer**: dyn-resume-compat-output.txt
- **Concern**: - **architecture** `scripts/ship-pr.sh:3213-3268` — `write_initial_state` and `require_key` were pruned consistently (`HAS_BUMP` / `BUMP_TYPE` / `NEW_VERSION` removed from `ship-pr-state.sh`; stubs live only in `write_postbump_state` → `postbump-state.sh` at `809-826`), and there are no unset `$HAS_BUMP` references under `set -u`. However, legacy keys left **inside** an existing `ship-pr-state.sh` are never stripped at load: extra keys are harmless, but stale `RESUME_PHASE` / `CALLER_KIND` can remain until bump entry or a successful `run_rebase_rebump` clear (`2684`), so a mid-CI stall can still expose `RESUME_PHASE=force-push-gate` + `CALLER_KIND=step8b_rebase` to the orchestrator even though Exit 5 / sub-procedure routing is gone. **Suggested fix:** After `validate_state_syntax` / `_ci_fix_pending_hydrate`, normalize legacy resume metadata once (mirror `_clear_phase1_postbump_residue`: blank `RESUME_PHASE`/`CALLER_KIND` when values are in the retired set, or when `PHASE` is not `bump` and `RESUME_PHASE` is not `ship-pr-rrr-phase14`), so persisted state cannot contradict Phase 1 semantics across CI phases.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] **`ship-pr-rrr-phase14` re-entry looks sound:** conflict exhaustion sets `RESUME_PHASE` + `CALLER_KIND=ship_pr_pre_push`, writes `ship-pr-rrr-after-phase14.flag`, and stalls; resume requires `--resume-phase ship-pr-rrr-phase14`, valid `PHASE` (`ci-initial|ci-merge`), and the flag; `run_rebase_rebump` then short-circuits through verify + `_run_rebase_rebump_from_step3` (`2680-2685`). `scripts/test-ship-pr-rebase.sh` pins the structural tokens and the missing-flag guard (case E).
- **Reviewer**: dyn-resume-compat-output.txt
- **Concern**: - **`ship-pr-rrr-phase14` re-entry looks sound:** conflict exhaustion sets `RESUME_PHASE` + `CALLER_KIND=ship_pr_pre_push`, writes `ship-pr-rrr-after-phase14.flag`, and stalls; resume requires `--resume-phase ship-pr-rrr-phase14`, valid `PHASE` (`ci-initial|ci-merge`), and the flag; `run_rebase_rebump` then short-circuits through verify + `_run_rebase_rebump_from_step3` (`2680-2685`). `scripts/test-ship-pr-rebase.sh` pins the structural tokens and the missing-flag guard (case E).
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] **Harness gap:** `test-ship-pr-rebase.sh` does not exercise legacy `--resume-phase` tolerance (`bump`, `force-push-gate`, `step8b_rebase`) or state-file-only stale `RESUME_PHASE` without argv — worth adding if you tighten normalization.
- **Reviewer**: dyn-resume-compat-output.txt
- **Concern**: - **Harness gap:** `test-ship-pr-rebase.sh` does not exercise legacy `--resume-phase` tolerance (`bump`, `force-push-gate`, `step8b_rebase`) or state-file-only stale `RESUME_PHASE` without argv — worth adding if you tighten normalization.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] **`scripts/ship-pr.md:128`** still documents `REBASE_COUNT >= 5` while `run_rebase_rebump` uses `_max_rebases=20` (`2692-2693`); pre-existing doc drift, not introduced by the resume-compat slice.
- **Reviewer**: dyn-resume-compat-output.txt
- **Concern**: - **`scripts/ship-pr.md:128`** still documents `REBASE_COUNT >= 5` while `run_rebase_rebump` uses `_max_rebases=20` (`2692-2693`); pre-existing doc drift, not introduced by the resume-compat slice.
- **Suggested revision**: Address the concern above.

