### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:1758-1828
- **Concern**: Behind count taken as raw command-substitution output. Scenario: Plan uses BEHIND=$(ci-behind-count.sh ...); the helper emits BEHIND_COUNT=<n> on the quiet FD-3 contract line. Assigning that string makes [[ BEHIND > 0 ]] / -gt comparisons wrong or always false, so the deferred rebase block never runs
- **Proposed resolution**: Parse like other helpers: _out=$("$SCRIPT_DIR/ci-behind-count.sh" ...) then BEHIND=$(kv_value BEHIND_COUNT "$_out") with a numeric default of 0

### FINDING_2:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:62-71
- **Concern**: CI_FIX_REBASE_PENDING is set immediately after deferred rebase, before post-rebase re-verify. Scenario: _verify_failed_jobs_locally ends with exit 3 on ci-local-unfixable (scripts/ship-pr.sh:2125), not a return code. After a deferred rebase the flag can already be true while the process exits 3 with a rebased unpushed tree. A later _stage_and_push can force-with-lease via the pending flag without a successful post-rebase verify/lint gate
- **Proposed resolution**: Set CI_FIX_REBASE_PENDING only when post-rebase _verify_failed_jobs_locally / run_checks_with_lint_fix_loop fail with return codes (e.g. 4 / 1), not unconditionally after run_rebase_rebump; rely on rebase happened this call for the success-path force push; clear the flag on exit 3 or do not set it until a failed return path

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:58-63,139-141
- **Concern**: Behind-check uses upstream/main for forks but deferred rebase calls run_rebase_rebump which always rebases onto origin/main. Scenario: FORKED_TARGET CI-fix runs can see BEHIND>0 vs upstream/main yet run_rebase_rebump/rebase-push.sh default to origin/main (ship-pr.sh:2666,2892; fork ACTION=rebase at 3142-3151 is a separate upstream-only path). Wrong base or false behind=0 risks skipped/wrong rebase and plain-push NF failures
- **Proposed resolution**: Thread --base-remote/--base-ref from read_state FORKED_TARGET through run_rebase_rebump into every rebase-push.sh call (and fix Edge cases: drop the claim that run_rebase_rebump already has fork handling)

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:1816-1947
- **Concern**: Deferred rebase runs after `LAST_STAGE_AND_PUSH_PRE_REFRESH_HEAD` is recorded, but `run_ci_fix_vendor` still compares `baseline_head` to that pre-rebase snapshot. Scenario: Vendor exit 0 with no new fix commit while `BEHIND>0`: deferred rebase rewrites `HEAD` but `baseline_head == pre_refresh_head`, triggering a false `first-fixer-non-health` bail (issue #3134 class)
- **Proposed resolution**: After a deferred rebase (and post-rebase re-verify), refresh `LAST_STAGE_AND_PUSH_PRE_REFRESH_HEAD` from current `HEAD`, or skip the no-commit bail when `CI_FIX_REBASE_PENDING` / a rebase occurred in this `_stage_and_push_ci_fixes` call

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:1758-1828;scripts/ship-pr.sh:2288-2312
- **Concern**: Post-rebase `_verify_failed_jobs_locally` inside `_stage_and_push_ci_fixes` lacks an explicit return-code contract; the per-job path only treats boolean success. Scenario: Post-rebase verify returns `2` (head-changed) or `4` (retry): `_stage_and_push` returns `1`, `run_evaluate_failure` increments `_fix_attempt` instead of `exit_stall` / `per_job_verification_retry`, diverging from `run_ci_fix_vendor` handling
- **Proposed resolution**: In `_stage_and_push_ci_fixes`, propagate verify `rc` (`2`/`4`/`3`); in `run_evaluate_failure` at the per-job `_stage_and_push_ci_fixes` call, mirror the existing `case` on `per_job_rc` / `vendor_rc`

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:1789-1814
- **Concern**: Plan reuses the pre-rebase `collect_ci_stage_paths` snapshot files after deferred rebase + second `run_checks_with_lint_fix_loop`. Scenario: `vendor_tracked` / `post-success` path lists reflect the pre-rebase tree; post-rebase lint deltas can be unstaged or wrong paths staged before force-push
- **Proposed resolution**: After post-rebase re-verify, re-capture dirty-path files (same helpers as the top of `_stage_and_push_ci_fixes`) and pass those into `collect_ci_stage_paths` for the lint-only commit

### FINDING_7:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:1758-1828
- **Concern**: Post-rebase `_verify_failed_jobs_locally` rc=2/4 not wired in the main `_stage_and_push_ci_fixes` change list or caller propagation. Scenario: Only Failure modes mention mapping rc=2→`exit_stall` and rc=4→failure; `_stage_and_push_ci_fixes` today returns 0/1 and `run_ci_fix_vendor`/`run_evaluate_failure` (2289-2337) treat any failure as rc=1—post-rebase head-changed (2) would not stall and rc=4 would not trigger `per_job_verification_retry`, breaking AC “re-verified on rebased tree before pushing”
- **Proposed resolution**: In `### UPDATED: scripts/ship-pr.sh` item 2, spell out a `case` on post-rebase `verify_rc` (skip push on non-zero; rc=2→`exit_stall`; rc=4→return 4); change `_stage_and_push_ci_fixes` to return 2/4; propagate through `run_ci_fix_vendor` and the per-job `_stage_and_push_ci_fixes` branch like the existing pre-push verify at 1923-1937
