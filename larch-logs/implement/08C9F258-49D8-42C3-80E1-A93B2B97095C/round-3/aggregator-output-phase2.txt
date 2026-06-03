Normalized findings from the supplied reviewer slots. Merged items share the same behavioral risk and fix; distinct code paths or fixes stay separate. `[OUT_OF_SCOPE]` headings are kept where any source carried that tag.

### FINDING_1: Bash substantive-attempt flag set before per-job / vendor outcome
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-python-parity-output.txt
- **Severity**: important
- **Concern**: Bash sets `_code_fix_attempted_on_ready_log` at per-job loop entry when `ci_failed_count > 0` and the TSV is non-empty, before `run_per_job_local_fix_loop` and before any vendor tier wins. Python sets `code_fix_attempted` only after `agents.run_waterfall` yields a `winning_tier` (post-waterfall gate). On ready logs + fixable jobs + all launcher tiers failing (`LAUNCHER_EXIT=1`), Bash can exit 3 with `ci-fix-exhausted` while tests (`test-ship-pr.sh:4280`, `ci_fix_fixable_launcher_only_exhausted`) and Python expect exit 4 stall / `waterfall-failed`. Bash vs Python ordering also inverts launcher-only semantics on the fixable-jobs + failed-vendors path. `ship-pr.md:130` documents entry-based flagging that conflicts with round-2 tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bash-python-parity-output.txt: Align the predicate in both trees: either move the Bash flag to after per-job machinery actually runs (e.g., per-job loop returns without immediate exhaustion, or `vendor_rc==4` / verification-retry consumption), or gate Python’s flag on per-job entry without requiring a winning vendor tier—matching the plan’s “entered `run_per_job_local_fix_loop` with `ci_failed_count > 0`” wording—and add/keep cross-tree tests for fixable jobs + all-fail launchers.

### FINDING_2: `needs_user_bail_reason` naming vs autonomous `ci-fix-exhausted`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `needs_user_bail_reason` includes autonomous tokens `ci-fix-exhausted` and `first-fixer-non-health`. The helper name may mislead orchestrators into assuming `BAIL_NEEDS_USER_INPUT=true` for `ci-fix-exhausted` despite the `is_autonomous` guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Duplicated jittered-backoff blocks in `run_evaluate_failure`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Four duplicated jittered-backoff blocks in `run_evaluate_failure`. Future defer/backoff tweaks require four edits and risk asymmetric sleep behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Python upfront log fetch when transient retry cap exhausted
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-bash-python-parity-output.txt
- **Severity**: latent
- **Concern**: Python always prefetches logs at `evaluate_failure` start; Bash skips the upfront `gh-run-logs.sh` block when `TRANSIENT_RETRIES >= 1`. Under exhausted transient budget, Python may perform an extra `gh` log fetch vs Bash on Phase 7 cutover. Stash/reuse behavior for blind rerun is otherwise aligned, but the extra upfront collect is a behavioral/API-call drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-bash-python-parity-output.txt: Optional parity: wrap the upfront `collect_failed_logs` call in the same `transient_retries < CI_MONITOR_TRANSIENT_RERUN_MAX` guard as the rerun branch, or document the extra fetch as an acceptable Python-only optimization.

### FINDING_5: Push-failure sets substantive flag in Python only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Push failure sets `code_fix_attempted_on_ready_log` in Python; Bash has no push-fail parity. When vendor wins but push fails, Python may route to fix-exhausted while Bash stalls (exit 4).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_6: Missing plan-named Python per-job exhaustion test
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Planned/new test `test_evaluate_failure_per_job_exhausted_routes_needs_user_input` is absent from `python/test_ci_monitor.py`. Per-job outer exhaustion without `verify-failed` is not explicitly locked in Python; traceability gap vs Bash `ci_fix_exhausted` coverage (`scripts/test-ship-pr.sh:3418-3486`). Existing `test_evaluate_failure_exhausted_routes_needs_user_input` requires a successful tier via `launch_fn`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Add the named test: ready logs+jobs, classified.fixable non-empty, per-job machinery runs, outer cap exhausts without verify-failed → fix-exhausted / NEEDS_USER_INPUT / ci-fix-exhausted.

### FINDING_7: Default `ci-failed-jobs` harness stub breaks fix-loop tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Default `ci-failed-jobs` harness stub returns `FAILED_JOBS_COUNT=0`; real `ci-failed-jobs.sh` is no longer copied in `write_subject`. `ci_per_job_*` fix-loop tests stub `gh` but expect real classifier behavior; `make test-ship-pr-fix-loop` may fail on per-job happy/unfixable paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Deterministic no-rerun test does not prove fix-first dispatch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deterministic no-rerun test does not assert fix-loop dispatch. Deterministic CI could skip rerun and stall without ever attempting lint/vendor/per-job fix, missing acceptance “fix-first.”
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: No regression test for upfront ready-log reuse on fix-loop iteration 1
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No test asserts upfront ready-log reuse on fix-loop iteration 1. Regression could re-fetch or misuse non-ready upfront capture undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: No Bash test for verification-retry substantive exhaustion (`vendor_rc==4`)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No Bash harness case for `vendor_rc==4` / verification-retry substantive exhaustion. Substantive exhaustion via verify-retry could drift from the Bash/Python contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Structural SKILL grep for autonomous bail tokens
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-implement-step8-exit3-first-fixer.sh` only greps `ci-fix-exhausted`. Orchestrator prose could drop autonomous `When` grouping while grep still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Autonomous CI-fix path and hostile CI log trust boundary
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `ci-fix-exhausted` now triggers autonomous main-agent CI-fix before `AskUserQuestion`, using redacted CI logs as primary context. Hostile repo CI jobs can embed instruction-like text; more deterministic failures reach substantive fix then autonomous exit-3 instead of blind rerun churn, increasing unprompted edit/push attempts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: Transient classification scans full log text
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `is_transient_net_signature` / transient blind-rerun classification scans full upfront CI log text (not tail-only / not redacted at classify time). Deterministic test output containing strings like `Connection timed out`, `EOF during`, or `HTTP 5xx` can false-positive as transient and consume blind rerun budget before fix-first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: `_ci_fix_pending_clear` at `run_evaluate_failure` entry drops persisted rebase-pending
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_ci_fix_pending_clear` at `run_evaluate_failure` entry drops persisted `CI_FIX_REBASE_PENDING`. After stall/kill with `pending=true` from a failed force-push following a verified fix, resume may skip the `CI_FIX_REBASE_PENDING` push-retry branch and leave fixes unpushed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: Bash `CI_FIX_REBASE_PENDING` sets substantive flag before readiness deferrals
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: important
- **Concern**: Bash `CI_FIX_REBASE_PENDING` branch at the top of each fix-loop iteration can set `_code_fix_attempted_on_ready_log=true` on `stage_rc==4` before `gh_logs_rc` / `ci_failed_rc` readiness deferrals. Python `evaluate_failure` has no equivalent pending-rebase path. A deferred Bash iteration can mark a substantive attempt without ready logs/jobs; Python would defer without setting the flag, changing terminal `ci-fix-exhausted` vs stall after `LARCH_SHIP_PR_IMPL=python` cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: Either port `CI_FIX_REBASE_PENDING` handling into `evaluate_failure` with the same readiness guards, or move the Bash flag assignment below the log/job-ready checks (and only set it when rebase-pending staging actually runs against ready failure data).

### FINDING_16: Python `local-unfixable` drops `code_fix_attempted_on_ready_log`
- **Reviewer(s)**: dyn-flag-threading-output.txt
- **Severity**: important
- **Concern**: After a winning vendor waterfall, Python sets `code_fix_attempted = True` when `classified.fixable` is non-empty, but the immediate `local-unfixable` return omits `code_fix_attempted_on_ready_log` (e.g. `per_job_command` returns `None`, `prepare_python_toolchain` fails, or initial unfixable list). `evaluate_failure` only ORs `fix.code_fix_attempted_on_ready_log`, so outer exhaustion can fall through to `waterfall-failed` / `STALLED` instead of `fix-exhausted` / autonomous `ci-fix-exhausted`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flag-threading-output.txt: Pass `code_fix_attempted_on_ready_log=code_fix_attempted` on the `local-unfixable` `FixResult` at line 943 (and mirror the same on `head-changed` at 948 if head drift can follow a per-job entry). Add a unit test where fixable jobs exist, the waterfall wins, prep fails, and `evaluate_failure` must return `fix-exhausted` after the outer cap.

### FINDING_17: `evaluate_failure` returns `local-unfixable` without consulting accumulated substantive flag
- **Reviewer(s)**: dyn-flag-threading-output.txt
- **Severity**: important
- **Concern**: `evaluate_failure` accumulates `code_fix_attempted_on_ready_log` across iterations, then returns immediately on `local-unfixable` without consulting the accumulator (e.g. attempt 1 `verify-failed` sets flag, attempt 2 `local-unfixable` without flag on `FixResult`). Monitor maps to `STALLED` and never reaches terminal `fix-exhausted` despite a prior substantive attempt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flag-threading-output.txt: Before `return fix` for `local-unfixable`, if `code_fix_attempted_on_ready_log` is already true, return `FixResult(status="fix-exhausted", detail="ci-fix-exhausted")` instead; or merge the accumulated flag into the returned `FixResult` and let the caller apply the same exhaustion routing as for `waterfall-failed`.

### FINDING_18: Python `upfront_ready_stash` omitted when transient cap already exhausted
- **Reviewer(s)**: dyn-upfront-stash-scope-output.txt
- **Severity**: important
- **Concern**: `upfront_ready_stash` is assigned only inside `if transient_retries < CI_MONITOR_TRANSIENT_RERUN_MAX`. When the transient budget is exhausted, Python still calls `collect_failed_logs` upfront but never stashes a ready result; fix-loop attempt 1 always re-collects. That contradicts `ship-pr.md:129` reuse prose for cap-exceeded skip and can defer attempt 1 if the second collect is `in_progress`/`error` despite an earlier ready capture. Bash skips the whole upfront block when `TRANSIENT_RETRIES >= 1`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-upfront-stash-scope-output.txt: Decouple stash from the rerun cap—e.g. after the rerun block, set `upfront_ready_stash = upfront_logs` when `upfront_logs.state == "ready"` and no transient blind rerun was submitted (preserve FINDING_6: do not stash after a rerun attempt, including failed rerun); alternatively skip the upfront collect entirely when `transient_retries >= CI_MONITOR_TRANSIENT_RERUN_MAX` for Bash parity. Add a unit test with `transient_retries=1`, a single mocked ready log response, and assert only one `gh run view … --log-failed` (or that attempt 1 uses the stash).

### OOS_1: [OUT_OF_SCOPE] `run_evaluate_failure` god-function shape
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Pre-existing god-function shape in `run_evaluate_failure` amplified by #3334 branches; harder to reason about fix-loop invariants. Follow-up extract: `classify_upfront`, `defer_attempt`, `terminal_exhaustion`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Branch bundles unrelated features vs main
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Multiple unrelated features/commits on the same branch (#3314, #3297, plan-review-loop, larch-logs, etc.). Reviewers/implementers may miss #3334 regressions; bisection and plan-fidelity sign-off on #3334 alone are harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Comment that `ci-fix-exhausted` in `needs_user_bail_reason` is autonomous
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `ci-fix-exhausted` appears in both `needs_user_bail_reason` and `is_autonomous_exit3_bail_reason`; future editors may assume it always sets `BAIL_NEEDS_USER_INPUT=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Parity scout: most checklist items aligned; predicate is main drift
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: nit
- **Concern**: For blind-rerun gating, ready-only upfront stash, deferrals, and terminal `ci-fix-exhausted` vs stall branching, Bash and Python are otherwise aligned; substantive-attempt predicate timing is the main decision-point drift.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] Intentional Python push-fail vs vendor-only stall test split
- **Reviewer(s)**: dyn-flag-threading-output.txt
- **Severity**: nit
- **Concern**: `test_evaluate_failure_push_failed_routes_fix_exhausted` vs `test_evaluate_failure_vendor_only_push_failed_stalls` split is intentional and correct for fixable vs empty jobs.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] Python flag propagation on verify/push/waterfall paths largely correct
- **Reviewer(s)**: dyn-flag-threading-output.txt
- **Severity**: nit
- **Concern**: `verify-failed`, `push failed`, and `pushed` propagate `code_fix_attempted_on_ready_log`; `waterfall-failed`, `first-fixer-non-health`, and pre-waterfall `local-unfixable` correctly omit it.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_7: [OUT_OF_SCOPE] Non-ready upfront stash behavior sound
- **Reviewer(s)**: dyn-upfront-stash-scope-output.txt
- **Severity**: nit
- **Concern**: Non-ready upfront logs are not stashed; attempt 1 correctly re-collects for in-progress/error upfront capture.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] No Bash “discard ready stash” defect on cap-exhausted path
- **Reviewer(s)**: dyn-upfront-stash-scope-output.txt
- **Severity**: nit
- **Concern**: Bash cap exhaustion skips the whole upfront block; no discard-ready-stash path (possible doc ambiguity only).
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_9: [OUT_OF_SCOPE] Existing tests would not catch upfront stash regression
- **Reviewer(s)**: dyn-upfront-stash-scope-output.txt
- **Severity**: nit
- **Concern**: Tests such as `test_evaluate_failure_exhausted_routes_needs_user_input` use `transient_retries=1` with identical mock responses on every collect, so they would not catch redundant re-fetch / ready-discard regression.
- **Suggested revisions (informational for voters; coder decides)**:
