### FINDING_1: code-quality: scripts/implement-bootstrap.sh:604-816
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] phase_plan_materialize is a ~210-line god function mixing I/O bail slug redaction and logging Phase 4 waterfall absorption or bail-path edits require editing one monolithic block with high regression risk Extract file-local helpers (derive_issue_branch_slug sanitize_markdown_file log_plan_materialize_warning) while keeping slug pipeline in one helper for B5-plan-green
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/implement/SKILL.md:344-388,495-539
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicated bootstrap exit-2 handler for initial plan call and dirty-tree resume A new STEP_FAILED branch added to one block is omitted from the other leaving resume paths without operator messaging Factor _ib_handle_bootstrap_exit2 used by both bootstrap invocations
- **Suggested revision**: Address the concern above.

### FINDING_3: correctness: scripts/implement-bootstrap.sh:747-749,784-794
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Inconsistent redaction failure policy tally fail-open summary fail-closed early return Transient redact-secrets failure skips larch:plan upsert after plan batches were written Align summary with tally fail-open raw body plus best-effort upsert or document fail-closed in implement-bootstrap.md
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/implement/SKILL.md:468
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Dirty-tree step 3 implies external checkpoint before resume but only bootstrap re-entry is shown Orchestrator may skip pre-resume checkpoint or violate line 763 by calling check-mid-run-dirty-tree separately Reword step 3 to bootstrap-only checkpoint or add explicit pre-resume fenced checkpoint block
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/implement-bootstrap.sh:977-1000
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] REPO_UNAVAILABLE snapshot guard triplicated in plan coder all arms Drift if one arm changes snapshot policy for repo-unavailable runs Hoist single guard before plan materialization dispatch
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/implement-bootstrap.sh:671,708
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] issue_title read twice from feature_file Minor duplication only No-op refactor read once and reuse
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: scripts/create-branch.sh:47
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Different branch slug pipeline than implement-bootstrap plan materialization Pre-existing naming divergence if scripts are consolidated later Consider shared slug helper in a follow-up outside Phase 3 scope
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/test-implement-bootstrap.sh:82-450
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Large inline stub matrix in build_sandbox Harness maintenance cost grows with each phase Pre-extract stubs to sourced file when Phase 4 expands cases
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/implement-bootstrap.sh:604-816
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Forked-target path leaves RUN_ID empty so write-tally best-effort fails /implement --forked N without --run-id yields empty RUN_ID in KV tail and no plan-review-tally.json while run-step1-plan-log still works Derive RUN_ID from --run-id then session-id then LARCH_TOKEN_SESSION_ID before write-tally and emit_final_tail
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/implement/SKILL.md:468
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Dirty-tree recovery prose implies a separate orchestrator checkpoint before resume Implementor may add a redundant or conflicting prompt-side dirty-tree call Say the clean re-check runs inside implement-bootstrap.sh --resume-plan-tail only
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/implement-bootstrap.sh:784-794
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Summary redaction failure early-returns without upsert-summary and has no harness coverage. A redact-secrets/tmpdir regression could skip the GitHub larch:plan summary while bootstrap still exits 0 and /implement proceeds to Step 2 without a failing test. Add B5-plan-summary-redaction-failure (or similar) stubbing redact failure during summary compose; assert Warning logged, no upsert-summary invoke, no larch:plan posted breadcrumb, rc 0.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:899-900
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] B5-plan-green does not assert timing-ledger plan-materialization mark in invoke log. Removal of timing-ledger mark call could slip past CI while token-ledger assertion still passes. Add assert_contains for timing-ledger mark implement Step 0 — plan materialization in B5-plan-green.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:1487-1540
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Breadcrumb tests omit branch breadcrumb variant without + plan logged when plan log fails. Regression could always emit + plan logged even when run-step1-plan-log.sh failed, misleading operators. Add Edge-breadcrumb-count-plan-log-fail with SANDBOX_RUN_PLAN_LOG_EXIT nonzero; assert branch breadcrumb lacks + plan logged.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:1104-1112
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No harness for --resume-plan-tail without session-env.sh. Misconfigured resume could panic or mis-route instead of exit 2 usage as documented in implement-bootstrap.sh:958. Add resume case with IMPLEMENT_TMPDIR set but no session-env.sh; assert exit 2 and usage message.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/implement-bootstrap.sh:619-668,512-544
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] --resume-plan-tail skips plan re-materialization while phase_tracking can re-adopt a different issue after sentinel mismatch, leaving stale plan.txt and feature-description.txt from the prior issue. Dirty-tree recovery re-runs bootstrap with the same IMPLEMENT_TMPDIR but a different --issue-number; Branch 2 adopts the new issue while Phase 3 tail reuses artifacts from the previous issue, misaligning Step 2 dispatch and plan-goals-test with the adopted issue. On --resume-plan-tail require parent-issue.md issue/run-id to match argv (fail closed on mismatch), forbid Branch-2 re-adoption during resume, or re-run the plan-materialization head whenever sentinel/plan artifacts do not match the requested issue.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/implement-bootstrap.sh:751-754
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] On forked-target-skip paths RUN_ID stays empty while write-tally.sh requires --run-id /implement --forked without --run-id: plan-goals-test may write via run-step1-plan-log internal resolve but write-tally fails best-effort; KV emits RUN_ID= empty; plan-review-tally.json and downstream manifest steps keyed on RUN_ID break Derive RUN_ID in phase_plan_materialize or emit_final_tail using --run-id then session-id then LARCH_TOKEN_SESSION_ID; extend B8-plan-forked-target to assert non-empty RUN_ID and write-tally --run-id
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/implement-bootstrap.sh:784-794
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Summary redaction failure returns 0 without tracking-issue-summary upsert and without bail Redaction pipe fails on larch-plan-summary: run continues with empty IMPLEMENT_BAIL_REASON; tracking issue never gets larch:plan marker though plan.txt exists; operator may not notice warning-only execution-issues entry Add orchestrator routing or safe fallback post path; mirror goal-text fail-closed pattern; add harness for summary redaction failure
- **Suggested revision**: Address the concern above.

### FINDING_18: architecture: scripts/implement-bootstrap.sh:960-965
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] --preflight-tmpdir only validated when --issue-number is set Direct bootstrap --up-to-phase plan without preflight flag attempts cp to /plan-from-issue.txt or empty-relative path with opaque copy-plan failure Require --preflight-tmpdir for all plan/coder/all invocations or validate directory exists before phase_plan_materialize
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] code-quality: scripts/implement-bootstrap.sh:698-704
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] branch-create-failed used for git-current-branch failures when create-branch was skipped Misleading bail label on forked/user-branch git probe failures; recovery messaging points at branch create Pre-existing; documented in SKILL.md:461; optional rename to branch-capture-failed
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] risk-integration: skills/implement/SKILL.md:468
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] External dirty-tree re-check before resume is prose-only not structurally enforced Orchestrator may skip pre-resume checkpoint; bootstrap re-check still blocks progress but recovery UX degrades Partially mitigated by test-implement-structure.sh pins; optional add grep for explicit check-mid-run-dirty-tree call before resume block
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Acceptance calls for `make test-implement-bootstrap` / `make lint` and a manual smoke run were not executed in this read-only review; harness coverage in-tree looks complete against the plan.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. Acceptance calls for `make test-implement-bootstrap` / `make lint` and a manual smoke run were not executed in this read-only review; harness coverage in-tree looks complete against the plan.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Step 0 still has a separate prompt-side Bash block for tracking token/timing marks (lines 697–714 in `SKILL.md`); the plan explicitly preserved that block, so it is not a fidelity gap vs the written plan (only vs the looser feature-description wording about “one Bash call”).
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. Step 0 still has a separate prompt-side Bash block for tracking token/timing marks (lines 697–714 in `SKILL.md`); the plan explicitly preserved that block, so it is not a fidelity gap vs the written plan (only vs the looser feature-description wording about “one Bash call”).
- **Suggested revision**: Address the concern above.

