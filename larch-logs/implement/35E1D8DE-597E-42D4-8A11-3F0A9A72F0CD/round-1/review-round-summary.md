# Review Round 1

- Mode: `diff`
- 21 accepted, 3 rejected (3 exonerated)

## Accepted Findings

### FINDING_1: Transient rerun failure aborts fix loop instead of falling through
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When `gh rerun` fails on the first transient attempt (`transient_retries=0`), Python returns `waterfall-failed` immediately instead of continuing into the vendor/local fix loop as bash `run_evaluate_failure` does. Rerun failure should be recorded/logged and execution should fall through to the outer fix loop; return `no-changes` only when rerun was submitted successfully.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: On rerun failure record/log and fall through to the outer fix loop; return no-changes only when rerun submitted successfully.
  - From cursor-specialist-edge-cases-output.txt: On rerun not submitted continue into outer fix loop; test rerun rc!=0 still invokes run_ci_fix


### FINDING_11: Missing `evaluate_failure` outer retry test (verify-failed then pushed)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test covers post-vendor make re-verify failing once then succeeding on second outer attempt. `evaluate_failure` could stop after first `verify-failed` and never re-drive waterfall—a regression vs `ship-pr` `vendor_rc=4` retry undetected until Phase 7 live CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stubbed evaluate_failure test: first outer verify-failed, second outer pushed; assert launch_fn count and fresh log/job fetches.


### FINDING_12: `monitor()` driver mapping largely untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Beyond merge/rebase_then_evaluate/fix-attempts bail, `monitor()` driver mapping is untested. Phase 7 driver could mis-map `pushed` fix to `STALLED`, `first-fixer-non-health` to `STALLED`, or timeout bail to `NEEDS_USER_INPUT` without pytest failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add monitor tests for pushed+goto_rebase, first-fixer NEEDS_USER_INPUT, poll timeout STALLED, evaluate_failure integration.


### FINDING_14: No `poll_ci` `NO_CHECKS` bail test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `NO_CHECKS` handling and fork grace path are untested. Regression could revert to wait loop or wrong `bail_reason`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub empty checks with grace>0; assert bail action and reason.


### FINDING_15: No `run_ci_fix` head-changed test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: HEAD movement during fix is untested. Could push stale commits or skip stall signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub rev-parse sequence; assert head-changed and no push.


### FINDING_16: No test for waterfall first-tier `short_circuited` / `first-fixer-non-health`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Pre-verify short-circuit could be conflated with post-stage no-op commit path without a dedicated test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub launch_fn tier-0 other failure; assert first-fixer-non-health without stage_and_push.


### FINDING_2: First-fixer short-circuit returns without rollback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When the waterfall short-circuits on the first tier with a non-health failure, Python returns `first-fixer-non-health` without calling `_rollback_to_baseline`, leaving vendor edits in the worktree. Bash restores baseline before this short-circuit return.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Call _rollback_to_baseline before returning FixResult on waterfall.short_circuited
  - From cursor-specialist-edge-cases-output.txt: Call _rollback_to_baseline before returning first-fixer-non-health from short_circuited path


### FINDING_21: Failure logs written outside `IMPLEMENT_TMPDIR` and not cleaned up
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_write_failure_log` stores redacted CI logs in system temp outside `IMPLEMENT_TMPDIR` required by `launch-*-ci.sh`. Phase 7 default `launch_fn` passes `--failure-log` under `/tmp`; launchers may die on validation; orphaned `*.redacted.log` files may retain partial CI secrets on shared hosts and are never deleted across fix cycles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Write failure logs under IMPLEMENT_TMPDIR (parity ship-pr.sh), pass only that path, delete after waterfall
  - From cursor-specialist-edge-cases-output.txt: Use per-run temp dir with finally cleanup


### FINDING_22: `plan_file` forwarded to launchers without `IMPLEMENT_TMPDIR` guard
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Malicious or mis-set `plan_file` (e.g. `~/.ssh/id_rsa`) could be cat'd into Cursor/Codex/Claude CI fixer prompts without validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate plan_file resolves under implement tmpdir and exists before build_launch_argv; else omit --plan-file


### FINDING_23: `_rollback_to_baseline` lacks submodule gitlink skip
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Bash `_ci_fix_rollback` skips submodule gitlinks; Python rollback runs `git checkout`/`rm` on gitlink paths and can corrupt submodule state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Skip paths where git ls-files --stage shows mode 160000; consider rejecting .. paths


### FINDING_26: No per-tier rollback after failed vendor attempts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Bash rolls back after each failed tier; Python leaves tier-1 edits on disk when tier-2 runs, causing wrong fixes or spurious verify failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Wrap launch_fn or waterfall to call _rollback_to_baseline (incl. staged) after each non-winning tier; add regression test


### FINDING_27: `baseline_staged` captured but never restored in rollback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Bash `_ci_fix_rollback` restores index state; Python only checkout/rm tracked and untracked paths, not staged snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Port staged snapshot and git restore --staged from bash _ci_fix_rollback into _rollback_to_baseline


### FINDING_28: `head-changed` returns without rollback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Vendor may have modified tree before HEAD check; driver sees stall signal but dirty tree persists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Roll back to baseline on head-changed before returning FixResult


### FINDING_29: Silent `behind_count=0` on `git rev-list` errors
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `git rev-list` failure with pass checks can yield merge while actually behind remote.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Log warning and/or force pending when behind computation fails


### FINDING_3: No driver signal when rerun is `already_running`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Python maps all non-submitted reruns to generic failure; the monitor/driver treats transient reruns as budget-consuming. When rerun is `already_running`, bash does not count it toward the transient budget and does not escalate prematurely. Python must expose `RerunResult.already_running` on `FixResult`/monitor and the driver must not count it toward the transient budget.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Expose RerunResult.already_running on FixResult/monitor; driver must not count it toward transient budget
  - From cursor-specialist-testing-output.txt: Expose already_running on FixResult; test monitor/evaluate_failure contract


### FINDING_4: Empty or missing `failed_run_id` crashes or invokes invalid `gh` calls
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When CI fails without a `runs/<id>` in the check link, `evaluate_failure` is invoked with an empty `run_id`, causing invalid `gh run view`/`rerun` calls or a `ValueError` via `int(run_id)`. Should bail with `STALLED`/`NEEDS_USER_INPUT` without `gh` calls when `failed_run_id` is None or empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Guard evaluate_failure: require status.failed_run_id or return STALLED without gh calls
  - From cursor-specialist-security-output.txt: Bail with STALLED/NEEDS_USER_INPUT when failed_run_id is None or empty before evaluate_failure
  - From cursor-specialist-edge-cases-output.txt: Validate run_id before evaluate_failure; return structured stall without gh calls when missing/invalid


### FINDING_5: Local-unfixable only after full vendor waterfall
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Python runs the full vendor waterfall before returning `local-unfixable`; bash skips vendors when jobs are unfixable-only (e.g., Gitleaks-only failure still launches cursor/codex/claude). Should return `local-unfixable` before `run_waterfall` when `fixable` is empty and `unfixable` is non-empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Return local-unfixable before run_waterfall when fixable is empty and unfixable is non-empty


### FINDING_6: Missing detached-HEAD guard in `evaluate_failure`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Bash blocks the fix loop on detached HEAD (`ship-pr.sh:2525-2530`); Python may run vendor/fix on detached HEAD and push from the wrong ref. Should check `symbolic-ref`/`current_branch` each outer attempt and return `STALLED` if not on a branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Check symbolic-ref/current_branch each outer attempt; STALLED if not on a branch
  - From cursor-specialist-edge-cases-output.txt: Add symbolic-ref check before outer fix attempts


### FINDING_7: `read_failed_jobs` silent on `gh` error (no warning parity)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When `gh jobs read` fails (non-in-progress), Python returns `([], error)` silently vs bash warning+continue. Empty jobs then trigger waterfall on no data; operators lose signal that the job list is empty due to `gh` failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Emit warning from runner capture before returning ([], error)
  - From cursor-specialist-testing-output.txt: Log warning via Runner; extend test_read_failed_jobs_error_empty
  - From cursor-specialist-edge-cases-output.txt: Emit warning on non-in-progress gh failure per bash parity


### FINDING_8: `stage_and_push` may push after failed commit when delta is empty
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Commit can fail with empty delta but push still runs; vendor edits may stay uncommitted while push proceeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Fail closed on commit failure; or skip commit/push when delta is empty per bash semantics


### FINDING_9: `read_failed_jobs` double-invokes `gh run view`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: On successful read, Python calls `gh.failed_jobs` after `failed_jobs_read`, paying 2× `gh run view` per read. The second call can diverge from the first and violates plan intent not to use `gh.failed_jobs`. Should parse jobs JSON from the first `failed_jobs_read` `CommandResult`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Parse jobs from first read or add gh parser helper
  - From cursor-specialist-edge-cases-output.txt: Parse jobs from first failed_jobs_read result
  - From cursor-specialist-plan-fidelity-output.txt: Parse jobs JSON from the failed_jobs_read CommandResult on rc==0


