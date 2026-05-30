### External Reviewer Issues

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/ship-pr.sh:1758-1828	Behind count taken as raw command-substitution output	Plan uses BEHIND=$(ci-behind-count.sh ...); the helper emits BEHIND_COUNT=<n> on the quiet FD-3 contract line. Assigning that string makes [[ BEHIND > 0 ]] / -gt comparisons wrong or always false, so the deferred rebase block never runs	Parse like other helpers: _out=$("$SCRIPT_DIR/ci-behind-count.sh" ...) then BEHIND=$(kv_value BEHIND_COUNT "$_out") with a numeric default of 0
2	in_scope	important	correctness	scripts/ship-pr.sh:1758-1828; scripts/ship-pr.sh:2889-3040	Fork behind base does not match deferred rebase base	Behind-check resolves upstream/main when FORKED_TARGET=true (mirrors ci_common_args), but run_rebase_rebump always calls rebase-push.sh without --base-remote upstream (ci-decide ACTION=rebase fork path uses upstream at 3142-3144). Branch can read behind vs upstream while rebasing onto origin/main	When FORKED_TARGET=true, pass --base-remote upstream --base-ref main into the deferred rebase path (thread through run_rebase_rebump or call the existing fork rebase-push shape before step 3) so behind-check and rebase share one base
3	in_scope	important	correctness	scripts/ship-pr.sh:1758-1828	CI_FIX_REBASE_PENDING can force-push without re-verify	After a deferred rebase, re-verify failure sets CI_FIX_REBASE_PENDING and skips push. A later _stage_and_push with behind=0 skips the rebase block but still force-pushes when the flag is set, without _verify_failed_jobs_locally / run_checks_with_lint_fix_loop	Pending-flag push must still run post-rebase re-verify (+ lint/stage) using failed_jobs_tsv before git-force-push.sh; only skip the second rebase when behind=0

1. **[correctness]** `scripts/ship-pr.sh:1758-1828` — Plan text `BEHIND=$(ci-behind-count.sh ...)` does not match the `BEHIND_COUNT=<n>` KV contract. Parse with `kv_value` (or grep/cut like `ci-wait.sh`) before comparing to zero.

2. **[correctness]** `scripts/ship-pr.sh:1758-1828`, `scripts/ship-pr.sh:2889-3040` — Fork edge case claims alignment with existing fork handling, but `run_rebase_rebump` never passes `--base-remote upstream` while behind-count and `ACTION=rebase` fork paths use `upstream/main`. Deferred CI-fix rebase can target the wrong remote.

3. **[correctness]** `scripts/ship-pr.sh:1758-1828` — `CI_FIX_REBASE_PENDING` + `behind=0` on a retry can force-push an unverified rebased tree, conflicting with failure-mode 1 (“do not push an unverified tree”). Gate pending-flag pushes on the same re-verify/lint block used after a fresh deferred rebase.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-edge-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-edge-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-edge-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-edge-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-edge-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	plan.txt:58-63,139-141	Behind-check uses upstream/main for forks but deferred rebase calls run_rebase_rebump which always rebases onto origin/main	FORKED_TARGET CI-fix runs can see BEHIND>0 vs upstream/main yet run_rebase_rebump/rebase-push.sh default to origin/main (ship-pr.sh:2666,2892; fork ACTION=rebase at 3142-3151 is a separate upstream-only path). Wrong base or false behind=0 risks skipped/wrong rebase and plain-push NF failures	Thread --base-remote/--base-ref from read_state FORKED_TARGET through run_rebase_rebump into every rebase-push.sh call (and fix Edge cases: drop the claim that run_rebase_rebump already has fork handling)
2	in_scope	latent	correctness	plan.txt:54-72,155-164	Post-rebase _verify_failed_jobs_locally rc=2/4 handling is only in Failure modes not in the _stage_and_push_ci_fixes steps	Implementer may return 1 from _stage_and_push and let run_evaluate_failure retry instead of exit_stall on head-changed (ship-pr.sh:2305-2311 pattern), leaving a deferred unpushed rebase in a retry loop	Add explicit verify_rc case handling to the ship-pr.sh _stage_and_push_ci_fixes bullet (rc=2 exit_stall; rc=4 return 1; no push) matching Failure modes 1

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-pragmatic-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-pragmatic-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/ship-pr.sh:1816-1947	Deferred rebase runs after `LAST_STAGE_AND_PUSH_PRE_REFRESH_HEAD` is recorded, but `run_ci_fix_vendor` still compares `baseline_head` to that pre-rebase snapshot	Vendor exit 0 with no new fix commit while `BEHIND>0`: deferred rebase rewrites `HEAD` but `baseline_head == pre_refresh_head`, triggering a false `first-fixer-non-health` bail (issue #3134 class)	After a deferred rebase (and post-rebase re-verify), refresh `LAST_STAGE_AND_PUSH_PRE_REFRESH_HEAD` from current `HEAD`, or skip the no-commit bail when `CI_FIX_REBASE_PENDING` / a rebase occurred in this `_stage_and_push_ci_fixes` call
1	in_scope	important	correctness	scripts/ship-pr.sh:1758-1828;scripts/ship-pr.sh:2288-2312	Post-rebase `_verify_failed_jobs_locally` inside `_stage_and_push_ci_fixes` lacks an explicit return-code contract; the per-job path only treats boolean success	Post-rebase verify returns `2` (head-changed) or `4` (retry): `_stage_and_push` returns `1`, `run_evaluate_failure` increments `_fix_attempt` instead of `exit_stall` / `per_job_verification_retry`, diverging from `run_ci_fix_vendor` handling	In `_stage_and_push_ci_fixes`, propagate verify `rc` (`2`/`4`/`3`); in `run_evaluate_failure` at the per-job `_stage_and_push_ci_fixes` call, mirror the existing `case` on `per_job_rc` / `vendor_rc`
1	in_scope	important	risk-integration	scripts/ship-pr.sh:1789-1814	Plan reuses the pre-rebase `collect_ci_stage_paths` snapshot files after deferred rebase + second `run_checks_with_lint_fix_loop`	`vendor_tracked` / `post-success` path lists reflect the pre-rebase tree; post-rebase lint deltas can be unstaged or wrong paths staged before force-push	After post-rebase re-verify, re-capture dirty-path files (same helpers as the top of `_stage_and_push_ci_fixes`) and pass those into `collect_ci_stage_paths` for the lint-only commit

**1. [correctness] `pre_refresh_head` vs deferred rebase (`scripts/ship-pr.sh:1816-1947`)**  
The plan inserts behind-check/rebase after `LAST_STAGE_AND_PUSH_PRE_REFRESH_HEAD` is set (today at line 1816) but leaves the vendor no-commit heuristic unchanged (`baseline_head` vs `pre_refresh_head` at 1931-1935). A deferred rebase can advance `HEAD` without a vendor fix commit, falsely matching the #3134 bail path.

**2. [correctness] Post-rebase verify exit codes (`scripts/ship-pr.sh:1758-1828`, `2288-2312`)**  
Failure modes describe mapping verify `rc=2`/`4`, but the `ship-pr.sh` update section does not require `_stage_and_push_ci_fixes` to return those codes or update the per-job caller at 2289 (which only branches on success vs retry). That breaks parity with `run_ci_fix_vendor` (1925-1930, 2325-2335).

**3. [risk-integration] Stale dirty-path snapshots for post-rebase lint (`scripts/ship-pr.sh:1789-1814`)**  
Reusing the existing `collect_ci_stage_paths` block with pre-rebase path list files after rebase + a second lint pass can miss or mis-stage post-rebase changes. Re-capture snapshots after post-rebase `run_checks_with_lint_fix_loop` before staging.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-state-key-lifecycle-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-state-key-lifecycle-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-state-key-lifecycle-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-state-key-lifecycle-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-state-key-lifecycle-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-state-key-lifecycle-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-state-key-lifecycle-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-dyn-state-key-lifecycle-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-state-key-lifecycle-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-state-key-lifecycle-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-test-list-fidelity-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-test-list-fidelity-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-test-list-fidelity-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-test-list-fidelity-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-test-list-fidelity-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-test-list-fidelity-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-test-list-fidelity-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-dyn-test-list-fidelity-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-test-list-fidelity-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-test-list-fidelity-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-waterfall-semantic-shift-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-waterfall-semantic-shift-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-waterfall-semantic-shift-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-waterfall-semantic-shift-output.txt.diag)

  ```
