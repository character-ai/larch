### FINDING_1: correctness: scripts/implement-bootstrap.sh:555-561,1004-1011
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] --resume-plan-tail still runs full phase_tracking Branch 1 resume path After dirty-tree bail on Branch 2 adopt, resume re-executes larch-log init and [IMPLEMENTING] rename despite plan/docs saying only Phase 3 tail resumes On RESUME_PLAN_TAIL=true rehydrate tracking IDs from sentinel without run_larch_log_init or rename_to_implementing; skip phase_tracking side effects
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: scripts/implement-bootstrap.sh:546-575
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New STEP_FAILED=resume-plan-tail-sentinel paths lack harness cases During dirty-tree recovery --resume-plan-tail can fail on sentinel mismatch/malformation with no offline regression test Add B15-B17 harness cases asserting exit 2 STEP_FAILED and no Phase 3 tail invocations
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: skills/implement/SKILL.md:339-383
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] _ib_handle_bootstrap_exit2 omits resume-plan-tail-sentinel branch Dirty-tree resume bootstrap exit 2 falls through to generic abort without normalized operator stdout message Add explicit STEP_FAILED=resume-plan-tail-sentinel case arm in handler
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:834-844
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] B5-all does not assert Phase 3 helpers skipped via invoke log tracking-init-failed could regress to running gh/persist while bail string stays correct Add assert_not_contains on invoke log for Phase 3 helpers
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: skills/implement/scripts/test-implement-bootstrap.md:20
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] GP-repo-unavail-plan doc contradicts snapshot behavior Maintainers may think repo-unavailable skips all Step 0 baseline work Reword case row to snapshot-only skip of gh/persist/plan materialization
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: scripts/implement-bootstrap.md:74-80
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Exit table omits resume-plan-tail-sentinel Contract doc incomplete for new fail-closed resume paths Document STEP_FAILED=resume-plan-tail-sentinel in exit codes section
- **Suggested revision**: Address the concern above.


### FINDING_24: architecture: scripts/implement-bootstrap.sh:572-575
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] --resume-plan-tail requires parent-issue.md but POSTED=false deletes the sentinel while Phase 3 still runs. Branch 2 metadata defer → dirty-tree at checkpoint → operator cleans tree → resume exits 2 with resume-plan-tail-sentinel; plan/branch tail never completes despite SKILL recovery flow. Skip sentinel requirement on resume when plan artifacts already exist in IMPLEMENT_TMPDIR and/or for DEFERRED paths without a sentinel; add B4-plan+dirty resume harness.
- **Suggested revision**: Address the concern above.


### FINDING_25: risk-integration: skills/implement/SKILL.md:467-495
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Dirty-tree recovery documents universal --resume-plan-tail re-entry but SKILL lacks exit-2 handling for resume-plan-tail-sentinel. POSTED=false dirty-tree resume aborts with generic exit 2; orchestrator gives no targeted operator message. Align SKILL with bootstrap capabilities; add _ib_handle_bootstrap_exit2 branch for STEP_FAILED=resume-plan-tail-sentinel.
- **Suggested revision**: Address the concern above.


### FINDING_26: correctness: scripts/implement-bootstrap.sh:644-646
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Invalid RUN_ID after resolve_run_id failure still flows into write-tally and larch:plan summary marker. Empty/invalid run id in tally JSON and <!-- larch:plan v1 runid= --> marker; wrong or colliding log paths. Skip tally/summary or stall when valid_run_id fails after resolution; log a Warning.
- **Suggested revision**: Address the concern above.


### FINDING_28: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Harness omits POSTED=false dirty-tree resume and resume-plan-tail-sentinel exit-2 cases. Regression can re-break deferred-metadata dirty-tree recovery without CI signal. Add harness cases for POSTED=false dirty resume and resume-plan-tail-sentinel.
- **Suggested revision**: Address the concern above.


### FINDING_29: correctness: skills/implement/SKILL.md:339-383
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] _ib_handle_bootstrap_exit2 lacks STEP_FAILED=resume-plan-tail-sentinel handling Dirty-tree recovery re-runs bootstrap with --resume-plan-tail; invalid/missing parent-issue.md yields STEP_FAILED=resume-plan-tail-sentinel and generic exit 2 without operator guidance Add exit-2 table row and _ib_handle_bootstrap_exit2 case; document in implement-bootstrap.md exit codes
- **Suggested revision**: Address the concern above.


### FINDING_31: architecture: scripts/implement-bootstrap.md:114
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Behavior map omits repo-unavailable snapshot path outside phase_plan_materialize Readers tracing REPO_UNAVAILABLE flows miss that snapshot runs from main() while phase 3 is skipped Add behavior-table row for repo-unavailable snapshot via ensure_untracked_baseline_snapshot in main()
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/implement/scripts/test-implement-bootstrap.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] harness omits POSTED=false + dirty-tree + --resume-plan-tail Regression for deferred dirty-tree recovery would not fail CI Add B4-plan-dirty-resume (POSTED=false dirty then resume-plan-tail should complete Phase 3 tail)
- **Suggested revision**: Address the concern above.


