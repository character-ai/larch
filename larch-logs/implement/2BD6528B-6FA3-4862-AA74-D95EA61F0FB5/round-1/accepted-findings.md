### FINDING_10: Missing control-character rejection test for target argv files
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: No test asserts that `lint-fix-loop.sh --target-cmd-args-file` rejects control characters with exit 2, leaving prompt-composition hardening unpinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_13: Per-job push path skips relevant-checks gate
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The per-job success path calls `_stage_and_push_ci_fixes` with empty `checks_site`, so fixes for specific failed jobs can be pushed without a full local relevant-checks/pre-commit gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_18: Shared helper has hidden global staging side effect
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `run_captured_cmd_then_fix_loop` appends to `ALL_LINT_FIX_DELTA_PATHS_FILE` inside the helper, contradicting the plan’s requirement that the shared helper remain a pure mechanic and staging aggregation happen at call sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_19: CI job class mapping lacks direct table-driven assertions
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Per-job `CLASS` mapping for all CI jobs is only indirectly covered, so job rename or classifier drift can slip past tests that never invoke each workflow job name.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_2: Per-job main-agent-required and dispatch-failed statuses become ci-local-unfixable
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `main-agent-required` is mapped through `dispatch-failed` into a `ci-local-unfixable:lint` exit 3 path when CODEX/CURSOR is absent, rather than using the intended main-agent/vendor/stall recovery path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_3: Per-job head-changed status exits as unfixable instead of stall
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `head-changed` from the per-job lint-fix loop is folded into the `ci-local-unfixable` bail path, producing exit 3 instead of the established `exit_stall`/HEAD-drift recovery semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: Verification phase does not honor the outer fix budget
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-control-flow-wiring-output.txt
- **Severity**: important
- **Concern**: Phase B verification can retry with fresh inner loop budgets, verify jobs that already failed Phase A, or bail after a verification-side fix without correctly re-entering/counting against the outer `_max_fix=3` budget.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-control-flow-wiring-output.txt: Address the concern above.


### FINDING_5: Drift coverage misses ship-pr per-job argv dispatch mapping
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The drift pin only covers `ci-failed-jobs.sh` classification, not `ship-pr.sh` `_per_job_argv`, so CI job rename or mapping drift can pass tests while `ship-pr` dispatches the wrong local command.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: Planned per-job ship-pr harness cases are missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-security-output.txt, dyn-sanitization-gaps-output.txt
- **Severity**: important
- **Concern**: Most planned per-job `ship-pr` harness coverage is absent, including verification regression, gh degrade, cap exhaustion, no-changes-after-fail, injection/malformed job pins, shard argv, and refactor parity cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-security-output.txt, dyn-sanitization-gaps-output.txt: Address the concern above.


### FINDING_7: Per-job success followed by push failure falls through to vendor recovery
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-control-flow-wiring-output.txt
- **Severity**: latent
- **Concern**: After the per-job loop succeeds, a failed `_stage_and_push_ci_fixes` does not terminate that branch and can fall through to `run_ci_fix_vendor`, layering vendor fixes or rollback behavior on top of locally green per-job fixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-control-flow-wiring-output.txt: Address the concern above.


