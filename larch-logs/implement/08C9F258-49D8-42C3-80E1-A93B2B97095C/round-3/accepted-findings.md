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


### FINDING_10: No Bash test for verification-retry substantive exhaustion (`vendor_rc==4`)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No Bash harness case for `vendor_rc==4` / verification-retry substantive exhaustion. Substantive exhaustion via verify-retry could drift from the Bash/Python contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


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


