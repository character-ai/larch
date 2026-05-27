### FINDING_1: risk-integration: skills/implement/SKILL.md:437-449
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 0 routes dirty-tree to an undefined AskUserQuestion recovery flow Bootstrap returns IMPLEMENT_BAIL_REASON=dirty-tree with exit 0; orchestrator is told to run existing recovery but implement SKILL has no questions env write or recovery actions unlike design Add Step 0 dirty-tree recovery prose (env file + sentinel + AskUserQuestion options) or a referenced implement/references doc
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:105-126
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No positive harness for create-branch --branch failure despite stub support and documented branch-create-failed bail create-branch.sh regression could drop STALL_TRACKING or bail KV while SKILL still routes to Step 18 cleanup Add B13-plan-branch-create with SANDBOX_CREATE_BRANCH_EXIT=1 asserting branch-create-failed STALL and no later Phase 3 helpers
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:684-696,822-838
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] B4-plan and B8-plan do not assert plan.txt and feature-description.txt exist on disk Step 2 dispatch could fail at runtime despite passing PLAN_FILE KV tail Add post-run file existence and content checks plus B4-plan invoke-log assertions for gh/persist on DEFERRED=true
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:374-380
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Dirty-tree stub cannot simulate non-zero check-mid-run-dirty-tree exit mapped to unknown in implement-bootstrap.sh:590-594 Helper exit-code contract change would not trip harness Extend stub with SANDBOX_DIRTY_EXIT and assert dirty-tree bail without STALL
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: scripts/implement-bootstrap.sh:163-167,403-407
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] REPO_UNAVAILABLE skips phase_plan_materialize but only tracking-phase harness exists Plan phase might run or skip incorrectly on repo-unavailable runs Add GP-repo-unavail-plan asserting Phase 3 helpers are not invoked
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:760-763
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Empty-slug fallback to issue not covered in slug matrix All-symbol titles could produce wrong branch names without failing CI Add B5-plan-green iteration expecting testuser/issue-123
- **Suggested revision**: Address the concern above.


### FINDING_19: security: skills/implement/SKILL.md:370-371
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] gh-issue-view failure surfaces raw gh stderr via cat without redaction. Failed gh issue view can write OAuth or proxy details into the operator transcript and session logs. Pipe gh-issue-view.stderr.log through redact-secrets.sh before display; fail closed with a generic message if redaction fails.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: scripts/implement-bootstrap.md:113-114
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Behavior table order disagrees with phase_plan_materialize (gh before copy) Operators/debuggers following the mapping table misread failure order when copy-plan vs gh-issue-view fails Add fenced recovery block or references/dirty-tree-recovery.md pinned by tests
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: scripts/implement-bootstrap.sh:549-570
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Phase 3 exit-2 paths do not emit IMPLEMENT_TMPDIR before aborting Orchestrator handles copy-plan/gh-issue-view with ${IMPLEMENT_TMPDIR:-} but that var is unset until KV parse succeeds; stderr logs exist on disk but are not surfaced Emit IMPLEMENT_TMPDIR (minimal diagnostic tail) before exit 2; parse IMPLEMENT_TMPDIR from _ib_out in SKILL exit-2 handlers
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: skills/implement/SKILL.md:437-449
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] dirty-tree routing references a non-existent implement recovery flow Bootstrap returns IMPLEMENT_BAIL_REASON=dirty-tree with partial artifacts; orchestrator has no documented AskUserQuestion/auto-discard procedure and may continue or halt ambiguously Add Step 0 dirty-tree recovery prose (or route to Step 18) matching design-style sentinels and actions
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: scripts/implement-bootstrap.sh:624-629
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] git-current-branch failure leaves BRANCH_NAME empty and continues Step 2/ship-pr hit branch mismatch or bump-branch-guard stalls after plan batches were written Fail closed with a new bail reason or reuse branch-create-failed; add harness coverage
- **Suggested revision**: Address the concern above.


### FINDING_25: architecture: scripts/implement-bootstrap.sh:711-712
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Plan-posted breadcrumb fires despite upsert skip/failure Operators see larch:plan posted while GitHub summary was skipped or logged as warning only Gate second breadcrumb on tracking-issue-summary success
- **Suggested revision**: Address the concern above.


### FINDING_26: correctness: skills/implement/SKILL.md:437-449
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan requires dirty-tree AskUserQuestion recovery with sentinel but SKILL only adds routing-guard prose; no implement dirty-tree recovery procedure exists Orchestrator gets IMPLEMENT_BAIL_REASON=dirty-tree without documented recovery steps and may continue incorrectly Add Step 0 dirty-tree recovery subsection (env file + sentinel + AskUserQuestion + restore/clean) mirroring design checkpoint pattern or shared reference
- **Suggested revision**: Address the concern above.


### FINDING_27: correctness: skills/implement/scripts/test-implement-bootstrap.sh:822-837
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] B8 acceptance requires feature-description.txt on disk; test only checks PLAN_FILE KV and gh invoke log Regression can drop feature-description write yet pass B8; Step 2 dispatch lacks required file Assert [ -f "$SANDBOX_TMP/feature-description.txt" ] (and optionally title line) in B8-plan-forked-target
- **Suggested revision**: Address the concern above.


### FINDING_28: correctness: skills/implement/scripts/test-implement-bootstrap.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] branch-create-failed bail documented and implemented but no harness case unlike B6/B7 create-branch failure handling can regress silently Add B13-plan-branch-create with SANDBOX_CREATE_BRANCH_EXIT non-zero asserting bail stall and no later helpers
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: skills/implement/SKILL.md:588
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale prose claims prompt owns post-bootstrap plan token/timing marks Plan materialization marks moved to bootstrap; only tracking marks remain below Reword to tracking-only token/timing marks
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: skills/implement/SKILL.md:437-449,662-664
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 0 dirty-tree bail has no concrete AskUserQuestion recovery and implementer waterfall lacks a dirty-tree gate Bootstrap returns IMPLEMENT_BAIL_REASON=dirty-tree after a dirty checkpoint; orchestrator has no documented recovery steps and waterfall prose still runs on paths continuing to Step 2, allowing implementation on a polluted tree or an indefinite halt Add explicit Step 0 dirty-tree recovery prose or script plus a waterfall guard that blocks until recovery completes
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: scripts/implement-bootstrap.sh:624-629
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] git-current-branch failure leaves BRANCH_NAME empty while phase continues Detached HEAD or git-current-branch failure after branch create yields empty BRANCH_NAME in KV tail; Step 2 dispatch and post-dispatch branch checks fail later Treat git-current-branch failure as a hard bail (STALL or exit 2 with STEP_FAILED) before plan logging
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: skills/implement/scripts/test-implement-bootstrap.sh:822-837
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] B8-plan-forked-target omits feature-description.txt assertion Acceptance requires forked paths materialize feature-description.txt; harness only checks PLAN_FILE Harness should assert feature-description.txt exists after B8-plan-forked-target
- **Suggested revision**: Address the concern above.


