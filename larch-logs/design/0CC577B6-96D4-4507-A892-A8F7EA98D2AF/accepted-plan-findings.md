### FINDING_1: BEHIND count not parsed from quiet contract output
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan assigns the raw output of `ci-behind-count.sh` to `BEHIND`, but the helper emits `BEHIND_COUNT=<n>` on the quiet FD-3 contract line. Using that string directly makes `[[ BEHIND > 0 ]]` / `-gt` comparisons wrong or always false, so the deferred rebase block never runs when it should.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Parse like other helpers: _out=$("$SCRIPT_DIR/ci-behind-count.sh" ...) then BEHIND=$(kv_value BEHIND_COUNT "$_out") with a numeric default of 0


### FINDING_2: CI_FIX_REBASE_PENDING set before post-rebase re-verify
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: The plan sets `CI_FIX_REBASE_PENDING` immediately after deferred rebase, before post-rebase re-verify. `_verify_failed_jobs_locally` can end with exit 3 on `ci-local-unfixable` (not a return code). After a deferred rebase the flag can already be true while the process exits 3 with a rebased unpushed tree; a later `_stage_and_push` can force-with-lease via the pending flag without a successful post-rebase verify/lint gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Set CI_FIX_REBASE_PENDING only when post-rebase _verify_failed_jobs_locally / run_checks_with_lint_fix_loop fail with return codes (e.g. 4 / 1), not unconditionally after run_rebase_rebump; rely on rebase happened this call for the success-path force push; clear the flag on exit 3 or do not set it until a failed return path


### FINDING_3: Fork behind-check vs rebase base mismatch
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The behind-check uses `upstream/main` for forks, but deferred rebase calls `run_rebase_rebump`, which always rebases onto `origin/main`. Fork `FORKED_TARGET` CI-fix runs can see `BEHIND>0` vs `upstream/main` yet `run_rebase_rebump` / `rebase-push.sh` default to `origin/main` (fork `ACTION=rebase` is a separate upstream-only path). Wrong base or false `behind=0` risks skipped/wrong rebase and plain-push NF failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Thread --base-remote/--base-ref from read_state FORKED_TARGET through run_rebase_rebump into every rebase-push.sh call (and fix Edge cases: drop the claim that run_rebase_rebump already has fork handling)


### FINDING_4: False first-fixer-non-health bail after deferred rebase
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Deferred rebase runs after `LAST_STAGE_AND_PUSH_PRE_REFRESH_HEAD` is recorded, but `run_ci_fix_vendor` still compares `baseline_head` to that pre-rebase snapshot. Vendor exit 0 with no new fix commit while `BEHIND>0`: deferred rebase rewrites `HEAD` but `baseline_head == pre_refresh_head`, triggering a false `first-fixer-non-health` bail (issue #3134 class).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: After a deferred rebase (and post-rebase re-verify), refresh `LAST_STAGE_AND_PUSH_PRE_REFRESH_HEAD` from current `HEAD`, or skip the no-commit bail when `CI_FIX_REBASE_PENDING` / a rebase occurred in this `_stage_and_push_ci_fixes` call


### FINDING_5: Post-rebase verify return codes not propagated to callers
- **Reviewer(s)**: Cursor-Pragmatic, unknown-slot
- **Severity**: important
- **Concern**: Post-rebase `_verify_failed_jobs_locally` inside `_stage_and_push_ci_fixes` lacks an explicit return-code contract wired through callers. The per-job path only treats boolean success; `_stage_and_push_ci_fixes` today returns 0/1 and `run_ci_fix_vendor` / `run_evaluate_failure` treat any failure as rc=1. Post-rebase verify returning 2 (head-changed) or 4 (retry) would not trigger `exit_stall` or `per_job_verification_retry`, diverging from existing pre-push verify handling and breaking the acceptance criterion that fixes are re-verified on the rebased tree before pushing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `_stage_and_push_ci_fixes`, propagate verify `rc` (`2`/`4`/`3`); in `run_evaluate_failure` at the per-job `_stage_and_push_ci_fixes` call, mirror the existing `case` on `per_job_rc` / `vendor_rc`
  - From unknown-slot: In `### UPDATED: scripts/ship-pr.sh` item 2, spell out a `case` on post-rebase `verify_rc` (skip push on non-zero; rc=2→`exit_stall`; rc=4→return 4); change `_stage_and_push_ci_fixes` to return 2/4; propagate through `run_ci_fix_vendor` and the per-job `_stage_and_push_ci_fixes` branch like the existing pre-push verify at 1923-1937


### FINDING_6: Stale stage-path snapshot after deferred rebase
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan reuses pre-rebase `collect_ci_stage_paths` snapshot files after deferred rebase and a second `run_checks_with_lint_fix_loop`. `vendor_tracked` / post-success path lists reflect the pre-rebase tree; post-rebase lint deltas can be unstaged or wrong paths staged before force-push.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: After post-rebase re-verify, re-capture dirty-path files (same helpers as the top of `_stage_and_push_ci_fixes`) and pass those into `collect_ci_stage_paths` for the lint-only commit

---

**Merge notes**: Input FINDING_5 and FINDING_7 describe the same behavioral risk (post-rebase verify rc=2/4 not wired through `_stage_and_push_ci_fixes` and callers) and were merged into FINDING_5 above. The other six input findings address distinct failure modes or code paths and remain separate.

