### FINDING_1: Vendor ci-local-unfixable does not exit 3
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements, Codex-Arch, Codex-Edge, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Cursor-Pragmatic, Cursor-dyn-rc-chain-integrity, Codex-dyn-rc-chain-integrity, Cursor-dyn-bash32-portability, Codex-dyn-bash32-portability
- **Severity**: important
- **Concern**: The planned vendor verification path sets `BAIL_REASON=ci-local-unfixable:*` and returns `1`, but `run_evaluate_failure` only treats `first-fixer-non-health` as an exit-3 user/action bail. The result can be retried until max retries, with `BAIL_REASON` cleared on the next attempt, and surface as stall exit 4 instead of the intended exit 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After vendor_rc=1, add the same exit 3 path as first-fixer (e.g. case "$(read_state BAIL_REASON)" in ci-local-unfixable:*) exit 3 ;; esac) or have _verify_failed_jobs_locally exit 3 like run_per_job_local_fix_loop.
  - From Cursor-Requirements: After vendor_rc=1, add the same exit 3 path as first-fixer (e.g. case "$(read_state BAIL_REASON)" in ci-local-unfixable:*) exit 3 ;; esac) or have _verify_failed_jobs_locally exit 3 like run_per_job_local_fix_loop.
  - From Codex-Arch: Extend the post-vendor BAIL_REASON dispatch to handle ci-local-unfixable:* with exit 3, or handle vendor_rc=1 by checking that prefix before incrementing _fix_attempt; update docs/tests for the exact exit contract.
  - From Codex-Edge: Extend the post-vendor BAIL_REASON dispatch to handle ci-local-unfixable:* with exit 3, or handle vendor_rc=1 by checking that prefix before incrementing _fix_attempt; update docs/tests for the exact exit contract.
  - From Cursor-Innovation: Match per-job contract: exit 3 from _verify_failed_jobs_locally (or run_ci_fix_vendor) when BAIL_REASON is ci-local-unfixable:*, and add run_evaluate_failure guard mirroring first-fixer-non-health if return-based
  - From Codex-Innovation: Add an explicit post-vendor branch for BAIL_REASON matching ci-local-unfixable:* that exits 3 immediately, or make run_ci_fix_vendor return a distinct rc and handle it before retry/backoff
  - From Cursor-Pragmatic: After vendor_rc=1 (and before _fix_attempt++), mirror first-fixer-non-health: if BAIL_REASON matches ci-local-unfixable* then exit 3; or have _verify_failed_jobs_locally exit 3 like run_per_job_local_fix_loop
  - From Cursor-dyn-rc-chain-integrity: Add vendor_rc=1) branch or post-vendor check: if BAIL_REASON matches ci-local-unfixable* then exit 3 (mirror run_per_job_local_fix_loop exit 3 at 2033), or have _verify_failed_jobs_locally exit 3 directly
  - From Cursor-dyn-rc-chain-integrity: Align with run_per_job_local_fix_loop:2033 (exit 3 after state_set_many) or document and implement explicit run_evaluate_failure bail handling before _fix_attempt increment
  - From Codex-dyn-rc-chain-integrity: Add an explicit vendor_rc=1 case that exits 3 for first-fixer-non-health and ci-local-unfixable:* before retrying, or make _verify_failed_jobs_locally exit 3 consistently with run_per_job_local_fix_loop
  - From Cursor-dyn-bash32-portability: Match run_per_job_local_fix_loop: call exit 3 after state_set_many for ci-local-unfixable, or add vendor_rc 1 branch in run_evaluate_failure that checks BAIL_REASON prefix and exits 3 before the fix loop continues
  - From Codex-dyn-bash32-portability: Add an explicit ci-local-unfixable route in run_evaluate_failure, or propagate a distinct rc such as 3 from the verifier/vendor path and exit 3 before incrementing _fix_attempt


### FINDING_2: Vendor verifier lacks final cross-job re-verification
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Codex-Requirements, Cursor-dyn-rc-chain-integrity, Codex-dyn-rc-chain-integrity, Codex-dyn-bash32-portability
- **Severity**: important
- **Concern**: The planned `_verify_failed_jobs_locally` checks jobs during repair but does not mirror `run_per_job_local_fix_loop`’s final sweep over previously passed jobs. A later local fix can regress an earlier originally failed job, yet the helper can return success and allow push without preserving the advertised rc=4 verification-regression behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Mirror phase_a_ok_jobs and phase_a_ok_shards in the new helper, rerun every locally-passed job after all fix loops, return 4 on regression, and plumb rc=4 through run_ci_fix_vendor/run_evaluate_failure as an outer retry without pushing.
  - From Cursor-Edge: run_per_job_local_fix_loop's second loop (lines 2006-2017) after all per-job fix loops, or return 4 and let run_evaluate_failure handle regression like the per-job path
  - From Codex-Edge: Mirror phase_a_ok_jobs/phase_a_ok_shards and rerun all locally verified jobs after all per-job fix loops, returning 4 on regression
  - From Codex-Innovation: Mirror run_per_job_local_fix_loop's phase_a_ok final sweep after all fix loops, and decide/handle rc=4 from run_ci_fix_vendor the same way the per-job path handles verification regressions
  - From Codex-Requirements: Add Phase B verification for jobs fixed by the helper, propagate rc=4 through run_ci_fix_vendor and run_evaluate_failure, and add a vendor_verify_regression test
  - From Cursor-dyn-rc-chain-integrity: Either omit rc=4 from the contract or implement post-loop verification + return 4 and handle it in run_evaluate_failure like per_job_rc=4
  - From Codex-dyn-rc-chain-integrity: Either remove rc=4 from the new helper contract, or add explicit 4) return 4 handling in run_ci_fix_vendor and a matching run_evaluate_failure case that preserves the intended retry semantics
  - From Codex-dyn-bash32-portability: Have _verify_failed_jobs_locally collect verified jobs and re-run a final sweep after all local fixes, then propagate rc=4 distinctly through run_ci_fix_vendor and run_evaluate_failure


### FINDING_3: max_iter env value is not concretely clamped
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Requirements, Cursor-dyn-rc-chain-integrity, Codex-dyn-bash32-portability
- **Severity**: important
- **Concern**: The plan mentions validating `LARCH_CI_LOCAL_FIX_ITER`/`_RCC_MAX_ITER` only as mitigation prose, not as an explicit edit. Non-numeric, empty, or zero values can cause arithmetic-loop errors or skip remediation instead of using a safe default.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Move the failure-mode mitigation into the concrete ship-pr.sh edits: clamp max_iter with case "$max_iter" in ''|*[!0-9]*|0) max_iter=3 ;; esac before the arithmetic loop, and add invalid/zero env coverage alongside rcc_max_iter_honored.
  - From Codex-Innovation: Add the max_iter numeric clamp in the actual UPDATED edit list and add a negative harness case for empty, zero, and non-numeric LARCH_CI_LOCAL_FIX_ITER values
  - From Cursor-Requirements: Add to edit #1: after max_iter=${_RCC_MAX_ITER:-3}, case "$max_iter" in ''|*[!0-9]*|0) max_iter=3 ;; esac (or reuse the same default as LARCH_CI_LOCAL_FIX_ITER:-6 at call sites)
  - From Cursor-dyn-rc-chain-integrity: Add the planned case clamp at run_captured_cmd_then_fix_loop entry (after max_iter=${_RCC_MAX_ITER:-3})
  - From Codex-dyn-bash32-portability: Add the case "$max_iter" in ''|*[!0-9]*|0) max_iter=3 ;; esac guard explicitly to edit 1 immediately after max_iter assignment, and test invalid values


### FINDING_4: Proposed vendor verification tests can no-op
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: latent
- **Concern**: Several proposed pass/exhaust/head-changed test setups use empty or unavailable failed-job TSV inputs while expecting `_verify_failed_jobs_locally` to run per-job commands. With no usable TSV rows, the helper can no-op, so the tests may pass without exercising the new pre-push verification gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Build the pass/exhaust/head-changed tests with a nonempty failed-jobs TSV and force vendor fallback through a real per-job rc=1 path, then assert the mapped local command runs after the launcher and before git-push.
  - From Codex-Requirements: Define the pass, exhaust, and head-changed tests with a non-empty failed-jobs TSV passed into the vendor path, such as a per-job rc=1 fallback scenario, and reserve empty TSV only for vendor_verify_empty_tsv


### FINDING_6: Target command args file is not written in helper
- **Reviewer(s)**: Codex-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The helper plan sets `_RCC_TARGET_CMD_ARGS_FILE=<args-file>` but does not explicitly call `_write_per_job_args_file` after `_per_job_argv` succeeds. The lint-fix loop may receive a missing or empty per-job command contract during vendor verification repairs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: In the new helper, assign args_file, call _write_per_job_args_file "$args_file" immediately after _per_job_argv succeeds, and add a test assertion that the lint-fix-loop stub receives a populated --target-cmd-args-file
  - From Cursor-Requirements: Specify the same args_file path pattern (per-job-${phase}-${job_token}-args.txt), call _write_per_job_args_file "$args_file" before run_captured_cmd_then_fix_loop, and document it in the helper bullet list


### FINDING_8: Plan/doc contract claims rc=4 without helper support
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Concern**: The plan intro says `_verify_failed_jobs_locally` returns the same codes as `run_per_job_local_fix_loop`, including rc=4, but the helper spec does not define a return-4 path. This creates a contract mismatch if verification regressions are intentionally mapped differently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Either drop return 4 from the intro contract or document why vendor-path verification maps regressions to unfixable[]/return 1 instead of return 4 and per_job_verification_retry


### FINDING_9: ship-pr.md docs omit vendor-path exit 3
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Concern**: The planned sibling doc update mentions rc=2 propagation but omits that vendor-path `ci-local-unfixable` must surface through the same exit 3 and `BAIL_REASON` contract as the per-job path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add to ship-pr.md / test-ship-pr.md updates: after vendor pre-push verification, ci-local-unfixable uses the same exit 3 + BAIL_REASON contract as run_per_job_local_fix_loop


### FINDING_10: Existing main-agent fallback test conflicts with new verifier behavior
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The test plan says to keep existing per-job tests unchanged, but the main-agent-required fallback test currently stubs the local lint command to keep failing while expecting vendor recovery and exit 0. Once TSV plumbing enables vendor verification, that path should re-run the failed job and bail, making the unchanged test invalid or masking the new behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Update the existing fallback test to either make the vendor fix cause the local job to pass and assert verification ran, or change the expected result to the new ci-local-unfixable bail


### FINDING_11: gh_logs_rc!=0 vendor branch does not preserve rc=2
- **Reviewer(s)**: Cursor-dyn-rc-chain-integrity, Codex-dyn-rc-chain-integrity
- **Severity**: important
- **Concern**: The plan adds a `run_ci_fix_vendor` rc=2 head-changed contract but leaves the `gh_logs_rc!=0` vendor call site as an implicit `elif`. A vendor return of 2 on that branch is treated as shell failure and can fall through to retry/max-retries instead of routing to the head-changed stall path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-rc-chain-integrity: Refactor scripts/ship-pr.sh:2131-2133 to the same run_ci_fix_vendor capture + case "$vendor_rc" pattern as the gh_logs_rc=0 else branch (0/2/1), or extract one shared helper for both call sites
  - From Codex-dyn-rc-chain-integrity: Refactor the gh_logs_rc!=0 fallback to capture vendor_rc and use the same explicit case "$vendor_rc" in 0|2|1|*) structure as the gh_logs_rc=0 vendor path, or funnel both vendor call sites through one helper


