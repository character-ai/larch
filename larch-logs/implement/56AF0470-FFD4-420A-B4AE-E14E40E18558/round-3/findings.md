### FINDING_1: **Important** `code-quality` `scripts/implement-bootstrap.sh:583-809` — `phase_plan_materialize` is a ~225-line function with 14+ locals that mixes hard failures (`exit 2`), bail returns (`run-flags-persist-failed`, `dirty-tree`, `branch-create-failed`), best-effort tails (`append-tool-failure.sh`), and breadcrumb side effects. That makes the Step 0 contract hard to reason about and will compound when Phase 4 adds more phases in the same file. **Suggested fix:** Split into small helpers aligned with the plan’s numbered steps (e.g. `plan_materialize_copy_and_fetch`, `plan_materialize_branch`, `plan_materialize_logs`, `plan_materialize_summary`) and keep `phase_plan_materialize` as a thin sequencer; preserve the existing harness order assertions.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **Important** `code-quality` `scripts/implement-bootstrap.sh:583-809` — `phase_plan_materialize` is a ~225-line function with 14+ locals that mixes hard failures (`exit 2`), bail returns (`run-flags-persist-failed`, `dirty-tree`, `branch-create-failed`), best-effort tails (`append-tool-failure.sh`), and breadcrumb side effects. That makes the Step 0 contract hard to reason about and will compound when Phase 4 adds more phases in the same file. **Suggested fix:** Split into small helpers aligned with the plan’s numbered steps (e.g. `plan_materialize_copy_and_fetch`, `plan_materialize_branch`, `plan_materialize_logs`, `plan_materialize_summary`) and keep `phase_plan_materialize` as a thin sequencer; preserve the existing harness order assertions.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Nit** `code-quality` `scripts/implement-bootstrap.sh:968-999` — The `plan` / `coder` / `all` arms each repeat the same `REPO_UNAVAILABLE` snapshot guard plus `should_run_phase_plan_materialize` / `phase_plan_materialize` block. **Suggested fix:** Extract a `maybe_run_plan_materialize_phase()` helper called from each arm to avoid drift when Phase 4 dispatch changes.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 2. **Nit** `code-quality` `scripts/implement-bootstrap.sh:968-999` — The `plan` / `coder` / `all` arms each repeat the same `REPO_UNAVAILABLE` snapshot guard plus `should_run_phase_plan_materialize` / `phase_plan_materialize` block. **Suggested fix:** Extract a `maybe_run_plan_materialize_phase()` helper called from each arm to avoid drift when Phase 4 dispatch changes.
- **Suggested revision**: Address the concern above.

### FINDING_3: **Nit** `code-quality` `scripts/implement-bootstrap.sh:664-701` — `issue_title` is read from `feature-description.txt` twice (`head -1` for slug derivation and again for goal text). **Suggested fix:** Read once after the resume gate and reuse the variable in both blocks.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 3. **Nit** `code-quality` `scripts/implement-bootstrap.sh:664-701` — `issue_title` is read from `feature-description.txt` twice (`head -1` for slug derivation and again for goal text). **Suggested fix:** Read once after the resume gate and reuse the variable in both blocks.
- **Suggested revision**: Address the concern above.

### FINDING_4: **Latent** `code-quality` `scripts/implement-bootstrap.sh:676-679` — `create-branch.sh` exit **1** (branch exists) and exit **2** (git failure) both map to the same `IMPLEMENT_BAIL_REASON=branch-create-failed` without the former SKILL.md operator-facing distinction. **Suggested fix:** If diagnostics matter, branch on `create_rc` (or parse `create-branch` stderr) to emit differentiated warnings while keeping a single bail reason, or document in `implement-bootstrap.md` that operators must read `create-branch.stderr.log`.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 4. **Latent** `code-quality` `scripts/implement-bootstrap.sh:676-679` — `create-branch.sh` exit **1** (branch exists) and exit **2** (git failure) both map to the same `IMPLEMENT_BAIL_REASON=branch-create-failed` without the former SKILL.md operator-facing distinction. **Suggested fix:** If diagnostics matter, branch on `create_rc` (or parse `create-branch` stderr) to emit differentiated warnings while keeping a single bail reason, or document in `implement-bootstrap.md` that operators must read `create-branch.stderr.log`. ---
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] **Nit** `code-quality` `skills/implement/scripts/test-implement-bootstrap.sh:82-509` — The sandbox now carries a large stub surface (~15 helpers + `gh`). This is appropriate for offline testing but increases maintenance cost for any script signature change. **Why out of scope:** harness expansion was plan-required; not a regression from Phase 3 logic itself.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **Nit** `code-quality` `skills/implement/scripts/test-implement-bootstrap.sh:82-509` — The sandbox now carries a large stub surface (~15 helpers + `gh`). This is appropriate for offline testing but increases maintenance cost for any script signature change. **Why out of scope:** harness expansion was plan-required; not a regression from Phase 3 logic itself.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: skills/implement/SKILL.md:473-479
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Dirty-tree resume uses ISSUE_NUMBER instead of TARGET_ISSUE_NUMBER for --issue-number. On --forked runs KV leaves ISSUE_NUMBER empty; recovery re-bootstrap gets --issue-number "" and upstream gh/plan tail fails. Use TARGET_ISSUE_NUMBER:-ISSUE_NUMBER pattern matching line 327 initial bootstrap.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/implement/SKILL.md:474
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Recovery snippet passes --caller-env "$CALLER_ENV" but orchestrator only defines CALLER_ENV_PATH/SESSION_ENV_PATH. Nested/forked run with caller-env on first pass loses caller context on dirty-tree resume. Reuse _ib_caller_env construction from lines 322-326 in recovery snippet.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/implement/SKILL.md:662
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Forked behavior table references ISSUE_NUMBER for get-issue-context; code uses ISSUE_NUMBER_OPT. Misleading operator/docs only; runtime uses argv issue correctly. Update table to reference argv/TARGET_ISSUE_NUMBER not KV ISSUE_NUMBER.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/implement-bootstrap.sh:954-957
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] --preflight-tmpdir only required when --issue-number set, not for all plan phases. Direct bootstrap --up-to-phase plan without --issue-number passes validation then fails at gh issue view. Require --preflight-tmpdir for plan/coder/all regardless of issue-number (with resume exception).
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/test-implement-structure.sh:379-402
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] test-implement-structure does not verify SKILL.md wires --preflight-tmpdir into the main bootstrap call via _ib_preflight Removing _ib_preflight from the Step 0 bash block would pass structure and most harness cases yet every live /implement run would fail at bootstrap argv validation after Preflight Add greps in test-implement-structure.sh for _ib_preflight array build and expansion in the non-resume implement-bootstrap invocation
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Phase 3 expanded the harness to ~136s on test-harnesses-7 while CI harness jobs use a 5-minute per-shard timeout Future case growth or slower runners could push shard 7 over the CI job limit and cause intermittent harness failures Monitor LARCH_HARNESS_TIMING for shard 7; reshard or split test-implement-bootstrap if wall time approaches the job timeout
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/implement/SKILL.md:462-479
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Dirty-tree recovery requires a pre-resume clean checkpoint re-run but that step is prose-only with no automated guard An orchestrator could call --resume-plan-tail without a clean re-check and proceed with a dirty worktree Add a structure or anti-halt harness assertion for an explicit dirty re-check bash block in the recovery gate or document and test the exception path
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/implement/SKILL.md:474
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Dirty-tree resume uses undefined $CALLER_ENV instead of CALLER_ENV_PATH/SESSION_ENV_PATH. Forked recovery resume omits caller-env; dynamic archetypes / timing-ledger forwarding can diverge from the first bootstrap pass. Reuse _ib_caller_env from the initial bootstrap block (or read path from session-env.sh) in the resume invocation; add harness coverage.
- **Suggested revision**: Address the concern above.

### FINDING_14: architecture: skills/implement/SKILL.md:470-489
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Resume bootstrap snippet lacks exit-2 handling present in the initial bootstrap wrapper. Resume get-issue-state/gate failure still parses KVs; orchestrator may continue with stale empty BRANCH_NAME after dirty-tree recovery. Mirror set +e, _ib_rc check, and STEP_FAILED branches from lines 344-388 around the resume call.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/implement/SKILL.md:464-479,scripts/implement-bootstrap.sh:658-661
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Dirty-tree recovery prose requires checkpoint re-probe but fenced Bash only shows --resume-plan-tail; bootstrap resume skips dirty check. Orchestrator may skip re-probe; tail steps run on a dirty tree without IMPLEMENT_BAIL_REASON=dirty-tree. Add fenced check-mid-run-dirty-tree re-probe before resume, or re-run checkpoint inside --resume-plan-tail before branch creation.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/implement-bootstrap.sh:248-280,658-661
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] --resume-plan-tail re-runs create-branch --check and session-entry-gate before plan tail. Clean mid-run checkpoint does not imply entry-gate pass; recovery can fail at infra after operator cleanup. Document gate vs checkpoint semantics, or skip re-gating on resume when session-env.sh exists.
- **Suggested revision**: Address the concern above.

### FINDING_17: architecture: scripts/implement-bootstrap.sh:690-697
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] git-current-branch empty/missing BRANCH reuses branch-create-failed bail reason. Operators cannot distinguish capture failure from create-branch failure in logs and routing tables. Introduce branch-capture-failed (or similar) with harness coverage.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/test-implement-bootstrap.sh:722-732
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] B3-plan IS_PR guard on plan phase already exists. N/A (observation only). No change required.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] architecture: skills/implement/SKILL.md:344-388
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] phase_infra STEP_FAILED=create-branch not in exit-2 handler table. Unrelated infra failure may get generic exit 2 without tailored operator text. Extend handler table (separate change).
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: skills/implement/SKILL.md:468 / scripts/implement-bootstrap.sh:598-661
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Dirty-tree recovery prose requires a clean checkpoint re-run before --resume-plan-tail but resume skips check-mid-run-dirty-tree and Step 0 structure test forbids a separate fenced re-check. Orchestrator follows only the resume bootstrap fence after operator cleanup; tree may still be dirty/unknown and phase tail runs create-branch and plan logging on a dirty worktree. Run check-mid-run-dirty-tree at the start of the --resume-plan-tail path in phase_plan_materialize (or add a structure-test-exempt recovery fence) and keep SKILL.md aligned.
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: scripts/implement-bootstrap.sh:140-163
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan step 13 emits two fixed breadcrumbs when LARCH_QUIET_BREADCRUMBS is set; implementation gates text on RUN_PLAN_LOGGED and PLAN_SUMMARY_POSTED. Operators expecting canonical step0 breadcrumb lines may not see larch:plan posted or + plan logged after best-effort sub-step failures. Emit both strings whenever breadcrumbs are enabled per plan or update plan/docs for success-gated variants.
- **Suggested revision**: Address the concern above.

