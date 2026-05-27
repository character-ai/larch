### FINDING_1: correctness: scripts/implement-bootstrap.sh:555-561,1004-1011
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] --resume-plan-tail still runs full phase_tracking Branch 1 resume path After dirty-tree bail on Branch 2 adopt, resume re-executes larch-log init and [IMPLEMENTING] rename despite plan/docs saying only Phase 3 tail resumes On RESUME_PLAN_TAIL=true rehydrate tracking IDs from sentinel without run_larch_log_init or rename_to_implementing; skip phase_tracking side effects
- **Suggested revision**: Address the concern above.

### FINDING_2: risk-integration: skills/implement/SKILL.md:471,473-511
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Dirty-tree recovery prose vs fence mismatch on pre-resume checkpoint Operator/agent may resume bootstrap without explicit clean checkpoint if following fence only Add check-mid-run-dirty-tree before resume block or state bootstrap is the only checkpoint
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/implement-bootstrap.sh:630-845
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Monolithic phase_plan_materialize with duplicated redact patterns Harder Phase 4 edits and inconsistent best-effort error handling across tally vs goal/summary Extract redact/tail helpers while keeping B5-plan-green ordering assertions
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/implement-bootstrap.sh:1006-1028
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Triplicated REPO_UNAVAILABLE snapshot guard in main Three identical if-blocks for plan/coder/all Single helper invoked once per dispatch branch
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/implement-bootstrap.sh:700,737
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate issue_title read from feature-description.txt Minor duplication in hot path Read once and reuse for slug and goal text
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: skills/implement/scripts/test-implement-bootstrap.sh:1124-1133
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] B7 missing-tmpdir case omits SANDBOX_TMP setup Order-dependent harness fragility after prior case rm -rf Allocate fresh SANDBOX_TMP before build_sandbox
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] correctness: scripts/implement-bootstrap.sh:619-622,572-575
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] POSTED=false clears sentinel before plan phase; resume-plan-tail requires sentinel Deferred metadata + dirty-tree recovery may fail closed on resume Document unsupported combo or retain sentinel for resume-only reads
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/test-implement-bootstrap.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] ~1.6k-line harness with heavy inline stubs Higher cost to extend Phase 4 tests Split stub bundle from assertion cases when touching harness again
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/implement/scripts/test-implement-bootstrap.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] harness omits POSTED=false + dirty-tree + --resume-plan-tail Regression for deferred dirty-tree recovery would not fail CI Add B4-plan-dirty-resume (POSTED=false dirty then resume-plan-tail should complete Phase 3 tail)
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

### FINDING_15: [OUT_OF_SCOPE] risk-integration: (branch)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Many non-Phase-3 commits in branch diff Unrelated harness/Makefile changes may fail CI independent of phase_plan_materialize Review or split unrelated commits for CI signal clarity
- **Suggested revision**: Address the concern above.

### FINDING_16: `gh issue view` uses numeric `--issue-number`, validated `--upstream-repo`, and a fixed template; no shell interpolation of issue content.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `gh issue view` uses numeric `--issue-number`, validated `--upstream-repo`, and a fixed template; no shell interpolation of issue content.
- **Suggested revision**: Address the concern above.

### FINDING_17: Branch slug pipeline sanitizes title to `[a-z0-9-]`; `create-branch.sh` enforces `${USER_PREFIX}/*` before `git checkout -b`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - Branch slug pipeline sanitizes title to `[a-z0-9-]`; `create-branch.sh` enforces `${USER_PREFIX}/*` before `git checkout -b`.
- **Suggested revision**: Address the concern above.

### FINDING_18: Goal text and operator stderr surfacing fail closed through `redact-secrets.sh` + `redact-tmpdir-paths.sh` (with placeholder / generic fallback).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - Goal text and operator stderr surfacing fail closed through `redact-secrets.sh` + `redact-tmpdir-paths.sh` (with placeholder / generic fallback).
- **Suggested revision**: Address the concern above.

### FINDING_19: `tracking-issue-summary.sh` re-redacts summary bodies before `gh` API calls even when bootstrap’s pre-post redaction step fails.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `tracking-issue-summary.sh` re-redacts summary bodies before `gh` API calls even when bootstrap’s pre-post redaction step fails.
- **Suggested revision**: Address the concern above.

### FINDING_20: `--resume-plan-tail` hard-fails on sentinel/issue mismatch (round 4), reducing cross-issue resume risk.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `--resume-plan-tail` hard-fails on sentinel/issue mismatch (round 4), reducing cross-issue resume risk.
- **Suggested revision**: Address the concern above.

### FINDING_21: `SECURITY.md` documents the Step 0 plan-materialization redaction contract.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `SECURITY.md` documents the Step 0 plan-materialization redaction contract.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/implement-bootstrap.sh:654-672` — `$IMPLEMENT_TMPDIR/feature-description.txt` is written with the full GitHub issue title/body and is consumed unredacted by Step 2 external implementers (`run-step2-dispatch.sh` → `step2-implement.sh`). This is the established `/implement` trust boundary (untrusted issue content → third-party APIs), not introduced by Phase 3 consolidation. **Suggested fix:** Only if product policy changes: add an optional redaction/sanitization pass before external dispatch, with explicit operator acknowledgment when plan/feature prose is truncated.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `scripts/implement-bootstrap.sh:941-943` — `--preflight-tmpdir` is required but not validated for session-tmpdir containment (contrast `implement-finalize.sh postbump` path guards). Normal `/implement` passes an `mktemp -d` preflight dir from the orchestrator, so practical risk is low unless the bootstrap CLI is invoked directly with attacker-controlled argv. **Suggested fix:** Reuse existing session-tmpdir containment helpers (or require the path to be a real directory under the caller’s preflight `mktemp` parent) before `cp "$PREFLIGHT_TMPDIR_OPT/plan-from-issue.txt"`.
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

### FINDING_27: architecture: scripts/implement-bootstrap.sh:727-734
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] git-current-branch failures reuse branch-create-failed bail reason. Detached HEAD or empty BRANCH KV misreported as branch creation failure in operator routing and logs. Split bail reason or document alias in implement-bootstrap.md and SKILL routing table.
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Harness omits POSTED=false dirty-tree resume and resume-plan-tail-sentinel exit-2 cases. Regression can re-break deferred-metadata dirty-tree recovery without CI signal. Add harness cases for POSTED=false dirty resume and resume-plan-tail-sentinel.
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: skills/implement/SKILL.md:339-383
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] _ib_handle_bootstrap_exit2 lacks STEP_FAILED=resume-plan-tail-sentinel handling Dirty-tree recovery re-runs bootstrap with --resume-plan-tail; invalid/missing parent-issue.md yields STEP_FAILED=resume-plan-tail-sentinel and generic exit 2 without operator guidance Add exit-2 table row and _ib_handle_bootstrap_exit2 case; document in implement-bootstrap.md exit codes
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: scripts/implement-bootstrap.md:70
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Plan promised unconditional plan-materialization breadcrumbs; code gates on helper success Misleading larch:plan posted breadcrumb on partial failure was the old risk; plan text no longer matches tested behavior Align plan/feature_description with conditional breadcrumb rules in implement-bootstrap.md
- **Suggested revision**: Address the concern above.

### FINDING_31: architecture: scripts/implement-bootstrap.md:114
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Behavior map omits repo-unavailable snapshot path outside phase_plan_materialize Readers tracing REPO_UNAVAILABLE flows miss that snapshot runs from main() while phase 3 is skipped Add behavior-table row for repo-unavailable snapshot via ensure_untracked_baseline_snapshot in main()
- **Suggested revision**: Address the concern above.

