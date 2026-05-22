### FINDING_1: code-quality: Makefile:4
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] test-persist-post-plan-keys remains on the mega-.PHONY line after its recipe and shard deps were removed make test-persist-post-plan-keys fails with no rule; contradicts plan to drop the target from .PHONY Remove test-persist-post-plan-keys from the .PHONY token list so phony declarations match existing recipes only
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/implement/scripts/run-step2-dispatch.md:16-25
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Contract still documents PLAN_FILE and POST_PLAN_WORKFLOW_PATH from session-env Readers and future edits trust session-derived plan/workflow wiring that run-step2-dispatch.sh no longer implements Rewrite Derived sources to match conventional plan.txt and hardcoded HARD workflow per run-step2-dispatch.sh
- **Suggested revision**: Address the concern above.

### FINDING_3: risk-integration: .claude-plugin/plugin.json:4
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Marketplace description still ties workflow depth to POST_PLAN_WORKFLOW_PATH from session/plan classification Consumers infer behavior and knobs that the retired classification path no longer drives Reword description for issue-anchored plan materialization and launcher-hardcoded Step 5 semantics
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: skills/implement/SKILL.md:42,1175
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Prose claims run-step5-review derives round-cap from POST_PLAN_WORKFLOW_PATH in session-env The launcher ignores that key; operators troubleshooting Step 5 cap follow the wrong contract Update NEVER #4 and Step 5 scripted-loop copy to match run-step5-review.sh and run-step5-review.md
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: docs/review-agents.md:102
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] POST_PLAN_WORKFLOW_PATH still described as Step 5 round-cap source Accepted OOS doc drift per implementation plan Track separate doc follow-up when tightening POST_PLAN references repo-wide
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: skills/shared/subskill-invocation.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Residual manifest heavy-phase wording Explicitly deferred in plan OOS_1 Future issue to align shared subskill doc with inline-only design
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: Makefile:4
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] `.PHONY` still names `test-persist-post-plan-keys` after the recipe and harness script were removed. Running `make test-persist-post-plan-keys` fails with no rule; contradicts plan to drop the target entirely. Remove `test-persist-post-plan-keys` from the mega-`.PHONY` line (and ensure no other stale references).
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: .claude-plugin/plugin.json:4
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Marketplace `description` still claims post-plan depth follows `POST_PLAN_WORKFLOW_PATH` from session/plan classification. Consumers or operators trust the blurb and audit the wrong session key; behavior is now hardcoded in `run-step5-review.sh`. Rewrite the description for issue-anchored plans, conventional `plan.txt`, and unified Step 5 without session-derived workflow path for the launcher.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/implement/SKILL.md:42,1175
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] SKILL.md still says Step 5 derives `--round-cap` from `POST_PLAN_WORKFLOW_PATH` while `run-step5-review.sh` hardcodes `WORKFLOW_PATH=HARD`. Operators mis-debug Step 5 caps by reading `POST_PLAN_WORKFLOW_PATH` in `session-env.sh` even though the launcher ignores it. Update those bullets to match `scripts/run-step5-review.sh` and the contract doc.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/ship-pr.sh:218-242
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] `resolve_plan_file` falls back to `plan.txt` only when `PLAN_FILE` is unset, not when it points at a missing under-tmpdir path. Legacy `PLAN_FILE=` plus missing file drops plan context for CI-fix/rebase paths even if `plan.txt` exists. After a missing-file warning, retry `$IMPLEMENT_TMPDIR/plan.txt` when present (and tighten docs).
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/run-step5-review.sh:128-134
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Unreachable `SIMPLE)` branch because `WORKFLOW_PATH` is always `HARD`. No user-visible failure today; confuses future edits. Simplify the `case` or justify both arms explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] correctness: docs/review-agents.md:102
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Still ties Step 5 `--round-cap` wording to `POST_PLAN_WORKFLOW_PATH`. Doc drift for operators reading review-agents. Accepted OOS_1/OOS_2 follow-up per plan; fix in a docs pass.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] risk-integration: skills/shared/subskill-invocation.md
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan notes possible stale manifest/persist references. Subagent docs may contradict retired surfaces. Handled as OOS_1 in plan; separate cleanup issue if desired.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: Makefile:4
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] `.PHONY` still names `test-persist-post-plan-keys` after the recipe and harness were deleted. `make test-persist-post-plan-keys` exits 0 with “Nothing to be done,” so the deleted regression suite is silently skipped and shard-coverage logic never inventories the name. Remove the stale `.PHONY` token and scan docs/scripts for that `make` target.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: .claude-plugin/plugin.json:4
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Marketplace `description` still claims Step 5 depth follows `POST_PLAN_WORKFLOW_PATH` from session/plan classification. Operators read the blurb while debugging, but `run-step5-review.sh` hardcodes `WORKFLOW_PATH="HARD"` and a conventional `plan.txt` path, so triage chases obsolete session-env semantics. Rewrite the description to match the implemented launcher behavior.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/design/scripts/design-driver.sh:60805-60811
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] `ACTION=CLASSIFY` is no longer dispatched; it becomes `ACTION_PASSTHROUGH`. Stale automation that still emits `CLASSIFY` silently skips classification instead of erroring, hiding mis-generated driver files. Fail closed on `CLASSIFY` or cover with a regression test asserting explicit failure.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/run-step5-review.sh:133
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Launcher only checks `-f` for `plan.txt`, not non-empty `-s`. Zero-byte `plan.txt` passes the gate and surfaces confusing failures deeper in review. Add a non-empty file check with a clear error if empty plans are plausible.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] risk-integration: docs/review-agents.md:102
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Doc still ties `--round-cap` to `POST_PLAN_WORKFLOW_PATH`; file untouched in this branch and listed as OOS follow-up in the plan. Readers get mismatched mental model vs current Step 5 script. Track separate doc PR per OOS_2.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] risk-integration: skills/shared/subskill-invocation.md
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Residual references to retired manifest/persist surfaces per plan OOS_1. Shared guidance slightly stale vs cutover. File/follow the accepted OOS issue when ready.
- **Suggested revision**: Address the concern above.

### FINDING_20: security: scripts/ship-pr.sh:218-243
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] resolve_plan_file skips conventional plan.txt when session PLAN_FILE is set but invalid. CI-fix / rebase paths may omit --plan-file while plan.txt exists under IMPLEMENT_TMPDIR, losing plan context for external agents. After invalid or missing session PLAN_FILE, fall back to IMPLEMENT_TMPDIR/plan.txt before returning empty.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] architecture: skills/shared/subskill-invocation.md
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Deferred doc may still mention retired manifest/persist surfaces. Confusing cross-references for readers; not changed in this branch. Track follow-up doc edit per backlog.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] architecture: docs/review-agents.md
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Deferred doc may still describe POST_PLAN_WORKFLOW_PATH for Step 5. Mismatched mental model vs code; not part of this diff. Track follow-up doc edit per backlog.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: Makefile:4
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Stale .PHONY entry test-persist-post-plan-keys after target removal make test-persist-post-plan-keys fails; drift vs harness coverage expectations Remove deleted targets from the mega-.PHONY line
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: skills/implement/SKILL.md:42,1175
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] SKILL.md still claims Step 5 round-cap is driven by session POST_PLAN_WORKFLOW_PATH run-step5-review.sh no longer reads that key; operators follow SKILL and mis-debug or re-plumb the wrong session key Reword NEVER #4 and the Step 5 review paragraph to match run-step5-review.sh (HARD + conventional plan.txt + degraded inflation)
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: Makefile:4
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] .PHONY still lists test-persist-post-plan-keys after the target and script were removed make test-persist-post-plan-keys / Makefile parsers can fail; phantom .PHONY Remove test-persist-post-plan-keys from the mega-.PHONY line
- **Suggested revision**: Address the concern above.

### FINDING_26: architecture: .claude-plugin/plugin.json:5
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Shipped plugin description still markets POST_PLAN_WORKFLOW_PATH session classification Consumer-facing metadata contradicts launcher behavior Rewrite description for issue-anchored plan + unified Step 5 without obsolete POST_PLAN_WORKFLOW_PATH sentence
- **Suggested revision**: Address the concern above.

### FINDING_27: architecture: git history (merge-base..HEAD)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Plan asked for a single atomic deletion+CI commit; branch has multiple commits including larch-logs chores Traceability and review scope blur vs plan delivery constraint Prefer squashing or isolating log/doc churn from the mechanical boundary retirement next time
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: skills/fix-issue/scripts/test-fix-issue-bail-detection.sh (no diff hunk)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Aggregate diff shows no harness edit for the stated --auto forward-assertion drop If main still pins --auto forwarding the plan item is unaddressed Verify main and update the harness if the assertion still exists
- **Suggested revision**: Address the concern above.

### FINDING_29: code-quality: scripts/run-step5-review.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Unreachable SIMPLE branch with WORKFLOW_PATH hardcoded to HARD Minor reader confusion Collapse case branches or document why SIMPLE remains
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] architecture: docs/review-agents.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] POST_PLAN_WORKFLOW_PATH mirror text deferred per plan OOS_2 N/A per explicit OOS Track via follow-up issue as planned
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] architecture: skills/shared/subskill-invocation.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Legacy manifest / persist prose deferred per plan OOS_1 N/A per explicit OOS Track via follow-up issue as planned
- **Suggested revision**: Address the concern above.

