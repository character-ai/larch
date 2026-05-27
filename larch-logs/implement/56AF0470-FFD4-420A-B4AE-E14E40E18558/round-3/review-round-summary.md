# Review Round 3

- Mode: `diff`
- 9 accepted, 9 rejected (8 exonerated)

## Accepted Findings

### FINDING_10: risk-integration: scripts/test-implement-structure.sh:379-402
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] test-implement-structure does not verify SKILL.md wires --preflight-tmpdir into the main bootstrap call via _ib_preflight Removing _ib_preflight from the Step 0 bash block would pass structure and most harness cases yet every live /implement run would fail at bootstrap argv validation after Preflight Add greps in test-implement-structure.sh for _ib_preflight array build and expansion in the non-resume implement-bootstrap invocation
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


### FINDING_20: correctness: skills/implement/SKILL.md:468 / scripts/implement-bootstrap.sh:598-661
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Dirty-tree recovery prose requires a clean checkpoint re-run before --resume-plan-tail but resume skips check-mid-run-dirty-tree and Step 0 structure test forbids a separate fenced re-check. Orchestrator follows only the resume bootstrap fence after operator cleanup; tree may still be dirty/unknown and phase tail runs create-branch and plan logging on a dirty worktree. Run check-mid-run-dirty-tree at the start of the --resume-plan-tail path in phase_plan_materialize (or add a structure-test-exempt recovery fence) and keep SKILL.md aligned.
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


