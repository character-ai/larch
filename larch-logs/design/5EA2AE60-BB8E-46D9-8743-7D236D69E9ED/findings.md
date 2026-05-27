### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2127-2137
- **Concern**: Vendor-path ci-local-unfixable never reaches exit 3. Scenario: _verify_failed_jobs_locally is specified to return 1 after state_set_many BAIL_REASON=ci-local-unfixable:…, but run_evaluate_failure only exits 3 for BAIL_REASON=first-fixer-non-health (2135-2136). run_per_job_local_fix_loop exits 3 directly (2033). vendor_verify_local_exhausts expects exit 3; without a matching branch the run retries up to _max_fix=3 and clears BAIL_REASON each attempt (2066).
- **Proposed resolution**: After vendor_rc=1, add the same exit 3 path as first-fixer (e.g. case "$(read_state BAIL_REASON)" in ci-local-unfixable:*) exit 3 ;; esac) or have _verify_failed_jobs_locally exit 3 like run_per_job_local_fix_loop.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2006-2015
- **Concern**: Finding 1: Proposed _verify_failed_jobs_locally omits the final per-job verification sweep that run_per_job_local_fix_loop uses.. Scenario: The plan claims matching rc=4 semantics, but the detailed helper verifies each job before its own fix loop and then moves on; a later fixable job can apply changes that regress an earlier originally-failed job, and relevant-checks may not cover it before push.
- **Proposed resolution**: Mirror phase_a_ok_jobs and phase_a_ok_shards in the new helper, rerun every locally-passed job after all fix loops, return 4 on regression, and plumb rc=4 through run_ci_fix_vendor/run_evaluate_failure as an outer retry without pushing.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch, Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:2135-2136
- **Concern**: Finding 2: The proposed ci-local-unfixable vendor result is not converted to exit 3.. Scenario: The plan has _verify_failed_jobs_locally set BAIL_REASON=ci-local-unfixable:<job> and return 1, but run_evaluate_failure only exits 3 for first-fixer-non-health; the new vendor_verify_local_exhausts case would retry until 10-max-retries/12-max-retries instead of surfacing the intended user/action bail.
- **Proposed resolution**: Extend the post-vendor BAIL_REASON dispatch to handle ci-local-unfixable:* with exit 3, or handle vendor_rc=1 by checking that prefix before incrementing _fix_attempt; update docs/tests for the exact exit contract.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/ship-pr.sh:174-181
- **Concern**: Finding 3: The numeric _RCC_MAX_ITER loop is introduced without making the validation an explicit code change.. Scenario: The plan raises _RCC_MAX_ITER from an env var but leaves max_iter=${_RCC_MAX_ITER:-3}; with LARCH_CI_LOCAL_FIX_ITER=0 or nonnumeric, the new arithmetic loop can skip remediation or error under set -u instead of using the safe default.
- **Proposed resolution**: Move the failure-mode mitigation into the concrete ship-pr.sh edits: clamp max_iter with case "$max_iter" in ''|*[!0-9]*|0) max_iter=3 ;; esac before the arithmetic loop, and add invalid/zero env coverage alongside rcc_max_iter_honored.

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-ship-pr.sh:3023-3062
- **Concern**: Finding 4: The proposed vendor_verify_local_pass setup examples would not exercise the new verifier.. Scenario: The plan suggests skipping the per-job path via an empty TSV or ci-failed-jobs.sh rc=1 while expecting _verify_failed_jobs_locally to run fixable jobs; in those scenarios the helper has no usable TSV rows and should no-op, so the test could pass without covering the new pre-push gate.
- **Proposed resolution**: Build the pass/exhaust/head-changed tests with a nonempty failed-jobs TSV and force vendor fallback through a real per-job rc=1 path, then assert the mapped local command runs after the launcher and before git-push.

### FINDING_6:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2006-2017
- **Concern**: Proposed _verify_failed_jobs_locally lacks Phase-B re-verification sweep. Scenario: Multi-job TSV: job B passes _run_per_job_command_once before job A's fix loop runs; A's lint-fix breaks B; helper returns 0 and _stage_and_push pushes a tree that still fails the originally-failed job
- **Proposed resolution**: run_per_job_local_fix_loop's second loop (lines 2006-2017) after all per-job fix loops, or return 4 and let run_evaluate_failure handle regression like the per-job path

### FINDING_7:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:1724-1728
- **Concern**: Verifier is planned before a later mutating lint-fix gate. Scenario: _stage_and_push_ci_fixes can run run_checks_with_lint_fix_loop after _verify_failed_jobs_locally; if that lint-fix changes shared files and regresses an originally failed job, the PR is pushed without re-running that job
- **Proposed resolution**: Move or repeat failed-job verification after the relevant-checks lint-fix gate, and rerun relevant-checks if the verifier itself applies changes before push

### FINDING_8:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2006-2016
- **Concern**: New verifier omits the existing final cross-job verification pass. Scenario: A later failed-job fix can regress an earlier job that already passed; the helper would return 0 even though it claims run_per_job_local_fix_loop-compatible rc=4 verification-regression semantics
- **Proposed resolution**: Mirror phase_a_ok_jobs/phase_a_ok_shards and rerun all locally verified jobs after all per-job fix loops, returning 4 on regression

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2031-2036,scripts/ship-pr.sh:2125-2137
- **Concern**: Planned _verify_failed_jobs_locally uses return 1 + state_set_many but not exit 3. Scenario: Unlike run_per_job_local_fix_loop (exit 3 at 2033), vendor path leaves run_evaluate_failure to retry up to _max_fix=3 and then exit_stall max-retries (exit 4), clearing BAIL_REASON each attempt; vendor_verify_local_exhausts cannot pass
- **Proposed resolution**: Match per-job contract: exit 3 from _verify_failed_jobs_locally (or run_ci_fix_vendor) when BAIL_REASON is ci-local-unfixable:*, and add run_evaluate_failure guard mirroring first-fixer-non-health if return-based

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2127-2138
- **Concern**: Finding 1: Vendor verifier ci-local-unfixable is not routed to exit 3. Scenario: _verify_failed_jobs_locally can set BAIL_REASON=ci-local-unfixable and return 1, but the proposed run_evaluate_failure handling only special-cases rc=0 and rc=2, then the next outer attempt clears BAIL_REASON at line 2066 and eventual exhaustion stalls as 10-max-retries instead of the planned uniform exit 3
- **Proposed resolution**: Add an explicit post-vendor branch for BAIL_REASON matching ci-local-unfixable:* that exits 3 immediately, or make run_ci_fix_vendor return a distinct rc and handle it before retry/backoff

### FINDING_11:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2006-2016
- **Concern**: Finding 2: New vendor verifier omits the existing final verification sweep. Scenario: The proposed helper verifies each failed job once, but if fixing a later failed job breaks an earlier one, the earlier job is never rerun before _stage_and_push_ci_fixes pushes
- **Proposed resolution**: Mirror run_per_job_local_fix_loop's phase_a_ok final sweep after all fix loops, and decide/handle rc=4 from run_ci_fix_vendor the same way the per-job path handles verification regressions

### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:1978-1986
- **Concern**: Finding 3: Target command args file is referenced but not written. Scenario: The helper plan sets _RCC_TARGET_CMD_ARGS_FILE=<args-file>, but does not explicitly create args_file with _write_per_job_args_file, so lint-fix-loop may receive a missing or empty per-job command contract during vendor verification repairs
- **Proposed resolution**: In the new helper, assign args_file, call _write_per_job_args_file "$args_file" immediately after _per_job_argv succeeds, and add a test assertion that the lint-fix-loop stub receives a populated --target-cmd-args-file

### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:174-181
- **Concern**: Finding 4: LARCH_CI_LOCAL_FIX_ITER validation is mentioned as mitigation but not covered by the concrete edit/test list. Scenario: The numeric arithmetic loop will read an env-controlled value; without an implemented and tested clamp, non-numeric input can abort under set -u or zero can silently skip all local repair attempts
- **Proposed resolution**: Add the max_iter numeric clamp in the actual UPDATED edit list and add a negative harness case for empty, zero, and non-numeric LARCH_CI_LOCAL_FIX_ITER values

### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2135-2138
- **Concern**: Plan sets BAIL_REASON=ci-local-unfixable and has run_ci_fix_vendor return 1 but never adds exit 3 handling in run_evaluate_failure. Scenario: vendor_verify_local_exhausts expects exit 3; today only run_per_job_local_fix_loop calls exit 3 (2033) and needs_user_bail_reason does not match ci-local-unfixable (1612-1616). Vendor path would increment _fix_attempt and eventually exit_stall 10-max-retries (exit 4) while clearing BAIL_REASON each loop (2066)
- **Proposed resolution**: After vendor_rc=1 (and before _fix_attempt++), mirror first-fixer-non-health: if BAIL_REASON matches ci-local-unfixable* then exit 3; or have _verify_failed_jobs_locally exit 3 like run_per_job_local_fix_loop

### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2037-2044
- **Concern**: _verify helper omits _write_per_job_args_file. Scenario: The helper spec sets _RCC_TARGET_CMD_ARGS_FILE=<args-file> but never calls _write_per_job_args_file (scripts/ship-pr.sh:1915-1920) as run_per_job_local_fix_loop does at scripts/ship-pr.sh:1978-1979; lint-fix-loop --target-cmd-args-file will be missing/empty and per-job verification cannot dispatch fixes
- **Proposed resolution**: Specify the same args_file path pattern (per-job-${phase}-${job_token}-args.txt), call _write_per_job_args_file "$args_file" before run_captured_cmd_then_fix_loop, and document it in the helper bullet list

### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:174-181
- **Concern**: max_iter sanity check listed only under failure modes. Scenario: Failure mode #2 (plan lines 92-93) requires clamping non-numeric/zero LARCH_CI_LOCAL_FIX_ITER before the new for ((attempt=1; attempt<=max_iter; attempt++)) loop, but UPDATED edit #1 (plan lines 33-34) does not include that guard; invalid env can yield zero iterations or bash arithmetic errors
- **Proposed resolution**: Add to edit #1: after max_iter=${_RCC_MAX_ITER:-3}, case "$max_iter" in ''|*[!0-9]*|0) max_iter=3 ;; esac (or reuse the same default as LARCH_CI_LOCAL_FIX_ITER:-6 at call sites)

### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/ship-pr.sh:1870-1871
- **Concern**: Verifier return captured via bare $?. Scenario: Plan uses case $? in immediately after _verify_failed_jobs_locally; any intervening command (including set -e traps) can clobber $? and mis-route rc=2 as rc=1
- **Proposed resolution**: Capture verify_rc=$? immediately after the call and case on verify_rc; have run_ci_fix_vendor return that value explicitly

### FINDING_18:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: correctness
- **Location**: plan.txt:14
- **Concern**: Intro claims return 4 but helper spec does not. Scenario: Approach line 14 says _verify_failed_jobs_locally returns the same codes as run_per_job_local_fix_loop including 4 (verification regression), but the helper spec (plan lines 37-44) never returns 4; per_job uses return 4 only in Phase B (scripts/ship-pr.sh:2014-2015)
- **Proposed resolution**: Either drop return 4 from the intro contract or document why vendor-path verification maps regressions to unfixable[]/return 1 instead of return 4 and per_job_verification_retry

### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: scripts/ship-pr.md:85-87
- **Concern**: ship-pr.md sibling update omits vendor-path exit 3. Scenario: Planned doc edits mention rc=2 propagation but not that vendor-path ci-local-unfixable must also surface as exit 3 (today only per-job path exit 3s via scripts/ship-pr.sh:2033)
- **Proposed resolution**: Add to ship-pr.md / test-ship-pr.md updates: after vendor pre-push verification, ci-local-unfixable uses the same exit 3 + BAIL_REASON contract as run_per_job_local_fix_loop

### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:1987-2016
- **Concern**: The proposed helper claims rc=4 verification-regression parity but omits the Phase B re-run. Scenario: The current per-job loop re-runs successful jobs and returns 4 on regression; the proposed _verify_failed_jobs_locally continues after _RCC_STATUS=ok without a final once-more verification, so a job can pass during the fix loop and regress before push
- **Proposed resolution**: Add Phase B verification for jobs fixed by the helper, propagate rc=4 through run_ci_fix_vendor and run_evaluate_failure, and add a vendor_verify_regression test

### FINDING_21:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-ship-pr.sh:3203-3252
- **Concern**: The test plan says keep existing per-job tests unchanged, but the main-agent-required fallback test will conflict with the new verifier. Scenario: That test currently stubs the local lint command to keep failing while expecting vendor recovery and exit 0; after TSV plumbing, the vendor verifier should re-run that same failed job and bail, so the unchanged test becomes invalid or masks the new behavior
- **Proposed resolution**: Update the existing fallback test to either make the vendor fix cause the local job to pass and assert verification ran, or change the expected result to the new ci-local-unfixable bail

### FINDING_22:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2082-2128
- **Concern**: The new vendor verification tests are described with empty or unavailable TSV setup that would not exercise verification. Scenario: Plan examples say per-job path skipped via TSV empty or ci-failed-jobs.sh rc=1 while expecting _verify_failed_jobs_locally to run fixable commands; in those paths the helper no-ops because there are no rows to iterate
- **Proposed resolution**: Define the pass, exhaust, and head-changed tests with a non-empty failed-jobs TSV passed into the vendor path, such as a per-job rc=1 fallback scenario, and reserve empty TSV only for vendor_verify_empty_tsv

### FINDING_23:
- **Reviewer(s)**: Cursor-dyn-rc-chain-integrity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2131-2134
- **Concern**: gh_logs_rc!=0 vendor call site keeps elif-then; plan only adds empty TSV arg and claims rc=2 uses the new case block. Scenario: Vendor returns 2 on the gh_logs_rc!=0 branch is treated as failure; no exit_stall 10-head-changed/12-head-changed (regression risk #2909)
- **Proposed resolution**: Refactor scripts/ship-pr.sh:2131-2133 to the same run_ci_fix_vendor capture + case "$vendor_rc" pattern as the gh_logs_rc=0 else branch (0/2/1), or extract one shared helper for both call sites

### FINDING_24:
- **Reviewer(s)**: Cursor-dyn-rc-chain-integrity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2066-2137
- **Concern**: Vendor verify exhaustion sets BAIL_REASON=ci-local-unfixable and returns 1, but run_evaluate_failure case only handles vendor_rc 0 and 2; line 2135 only keys first-fixer-non-health. Scenario: vendor_verify_local_exhausts expects exit 3; actual path clears BAIL_REASON next loop iteration (2066) and ends in exit_stall max-retries (exit 4)
- **Proposed resolution**: Add vendor_rc=1) branch or post-vendor check: if BAIL_REASON matches ci-local-unfixable* then exit 3 (mirror run_per_job_local_fix_loop exit 3 at 2033), or have _verify_failed_jobs_locally exit 3 directly

### FINDING_25:
- **Reviewer(s)**: Cursor-dyn-rc-chain-integrity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:17-18,44,50-52
- **Concern**: Plan claims uniform ci-local-unfixable surface but per-job path exits 3 while vendor path only returns 1 through run_ci_fix_vendor. Scenario: Operator and /implement Step 8 see stall exit 4 instead of user-input exit 3 for vendor-local-unfixable failures
- **Proposed resolution**: Align with run_per_job_local_fix_loop:2033 (exit 3 after state_set_many) or document and implement explicit run_evaluate_failure bail handling before _fix_attempt increment

### FINDING_26:
- **Reviewer(s)**: Cursor-dyn-rc-chain-integrity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:1870-1871,50-52
- **Concern**: run_ci_fix_vendor propagation uses case $? in immediately after _verify_failed_jobs_locally; run_evaluate_failure case has no 1|*) arm. Scenario: Fragile if any statement is inserted between call and $?; vendor_rc=1 behavior is implicit fall-through only
- **Proposed resolution**: Capture verify_rc=$? right after _verify_failed_jobs_locally; in run_evaluate_failure add explicit 1) arm (ci-local-unfixable / generic failure) before esac

### FINDING_27:
- **Reviewer(s)**: Cursor-dyn-rc-chain-integrity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:1870-1871,14,40-44
- **Concern**: run_ci_fix_vendor plans case $? in ... 1|*) return 1; plan intro lists helper rc=4 but spec never returns 4. Scenario: Any future rc=4 (verification regression parity) is collapsed to rc=1 and loses per_job_rc=4 retry semantics (2117-2118)
- **Proposed resolution**: Either omit rc=4 from the contract or implement post-loop verification + return 4 and handle it in run_evaluate_failure like per_job_rc=4

### FINDING_28:
- **Reviewer(s)**: Cursor-dyn-rc-chain-integrity
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:174-181,92-93
- **Concern**: max_iter sanity clamp is listed under Failure modes but not in actionable edit 1 for run_captured_cmd_then_fix_loop. Scenario: LARCH_CI_LOCAL_FIX_ITER=0 or non-numeric can make for ((attempt=1; attempt<=max_iter)) hang or no-op
- **Proposed resolution**: Add the planned case clamp at run_captured_cmd_then_fix_loop entry (after max_iter=${_RCC_MAX_ITER:-3})

### FINDING_29:
- **Reviewer(s)**: Cursor-dyn-rc-chain-integrity
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/ship-pr.sh:2063,2127-2129
- **Concern**: local vendor_rc is sufficient for the gh_logs_rc=0 else branch; vendor_rc unset on 2131 path if later code reads it. Scenario: Unlikely today but brittle if both vendor paths are unified incompletely
- **Proposed resolution**: Initialize vendor_rc= at loop top or only read vendor_rc inside each branch that sets it

### FINDING_30:
- **Reviewer(s)**: Codex-dyn-rc-chain-integrity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2131-2137
- **Concern**: The plan leaves the gh_logs_rc!=0 vendor call as an implicit elif while adding a run_ci_fix_vendor rc=2 contract. Scenario: If run_ci_fix_vendor returns 2 at this call site, shell truthiness treats it as false and falls through to retry or max-retries instead of routing head-changed to exit_stall like scripts/ship-pr.sh:2113-2116 and _rcc_handle_fix_status at scripts/ship-pr.sh:147-153
- **Proposed resolution**: Refactor the gh_logs_rc!=0 fallback to capture vendor_rc and use the same explicit case "$vendor_rc" in 0|2|1|*) structure as the gh_logs_rc=0 vendor path, or funnel both vendor call sites through one helper

### FINDING_31:
- **Reviewer(s)**: Codex-dyn-rc-chain-integrity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:2023-2033,2127-2138
- **Concern**: The proposed verifier sets BAIL_REASON=ci-local-unfixable:* and returns 1, but run_evaluate_failure only exits 3 for first-fixer-non-health. Scenario: When vendor_verify_local_exhausts happens, run_evaluate_failure will clear BAIL_REASON on the next loop attempt and can end as max-retries instead of surfacing the detail log; this differs from the existing per-job unfixable path, which exits 3 at scripts/ship-pr.sh:2033
- **Proposed resolution**: Add an explicit vendor_rc=1 case that exits 3 for first-fixer-non-health and ci-local-unfixable:* before retrying, or make _verify_failed_jobs_locally exit 3 consistently with run_per_job_local_fix_loop

### FINDING_32:
- **Reviewer(s)**: Codex-dyn-rc-chain-integrity
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/ship-pr.sh:1870,2013-2016
- **Concern**: The plan advertises _verify_failed_jobs_locally as returning the same rc set as run_per_job_local_fix_loop including rc=4, but the proposed run_ci_fix_vendor boundary maps 1|* to 1. Scenario: If the helper implementation follows the stated rc=4 contract for verification regression, the vendor path silently collapses it to rc=1 and cannot mirror the existing per-job rc=4 branch at scripts/ship-pr.sh:2117-2119
- **Proposed resolution**: Either remove rc=4 from the new helper contract, or add explicit 4) return 4 handling in run_ci_fix_vendor and a matching run_evaluate_failure case that preserves the intended retry semantics

### FINDING_33:
- **Reviewer(s)**: Cursor-dyn-bash32-portability
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2036-2044 (proposed _verify_failed_jobs_locally)
- **Concern**: Unfixable consolidation uses return 1 but sibling run_per_job_local_fix_loop exits 3. Scenario: run_per_job_local_fix_loop calls exit 3 after setting BAIL_REASON (scripts/ship-pr.sh:2023-2033); proposed helper returns 1 and run_evaluate_failure edit 5 only branches vendor_rc 0 and 2 (plan lines 50-52), so ci-local-unfixable vendor path retries up to _max_fix instead of exiting 3 with bail state
- **Proposed resolution**: Match run_per_job_local_fix_loop: call exit 3 after state_set_many for ci-local-unfixable, or add vendor_rc 1 branch in run_evaluate_failure that checks BAIL_REASON prefix and exits 3 before the fix loop continues

### FINDING_34:
- **Reviewer(s)**: Codex-dyn-bash32-portability
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:174-181
- **Concern**: Max-iter clamp is only in failure-mode prose, not in the scripts/ship-pr.sh edit steps. Scenario: The proposed arithmetic for loop is Bash 3.2-compatible, but with set -u a nonnumeric LARCH_CI_LOCAL_FIX_ITER such as abc aborts in arithmetic evaluation if the clamp is omitted
- **Proposed resolution**: Add the case "$max_iter" in ''|*[!0-9]*|0) max_iter=3 ;; esac guard explicitly to edit 1 immediately after max_iter assignment, and test invalid values

### FINDING_35:
- **Reviewer(s)**: Codex-dyn-bash32-portability
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2125-2137
- **Concern**: Vendor verifier unfixable return is collapsed into ordinary retry/stall handling. Scenario: The plan says ci-local-unfixable should surface uniformly as exit 3, but _verify_failed_jobs_locally returns 1, run_ci_fix_vendor returns 1, and run_evaluate_failure only exits 3 for first-fixer-non-health, so the run can retry and end as 10-max-retries instead
- **Proposed resolution**: Add an explicit ci-local-unfixable route in run_evaluate_failure, or propagate a distinct rc such as 3 from the verifier/vendor path and exit 3 before incrementing _fix_attempt

### FINDING_36:
- **Reviewer(s)**: Codex-dyn-bash32-portability
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2006-2016
- **Concern**: The new verifier does not preserve the existing final verification sweep / rc=4 contract. Scenario: A later per-job fix can regress an earlier job that already passed; the plan promises rc=4 but the detailed helper only checks each job once and run_ci_fix_vendor collapses 1|*
- **Proposed resolution**: Have _verify_failed_jobs_locally collect verified jobs and re-run a final sweep after all local fixes, then propagate rc=4 distinctly through run_ci_fix_vendor and run_evaluate_failure
