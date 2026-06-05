### FINDING_1: Postmerge run-log recovery/manifest handling must be centralized before report rendering
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-dyn-state-plumbing, Codex-dyn-state-plumbing
- **Severity**: important
- **Concern**: Multiple postmerge/run-log paths can render final reports or write done manifests after recovery/manifest failure, or rely on ship.py-only ordering while the side effects live inside run_logs helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add flush_logs_post reorder (or a postmerge-only helper) to the plan under python/run_logs.py; write manifest before _write_final_report
  - From Codex-Arch: Add an explicit run_logs.py step to refactor flush_logs_post or add a narrow helper so recovery plus manifest write happens before _write_final_report/_render_* calls, and have ship.py call that path.
  - From Cursor-dyn-state-plumbing: In run_logs.py extend the UPDATED section: flush_logs_post must fail-closed (RefreshSkip or no done write) when recovery_ok is false; apply the same rule to flush_logs_pre and update_manifest or document a single internal helper all paths use
  - From Codex-dyn-state-plumbing: Centralize fail-closed handling in run_logs: when recovery_ok is false, flush_logs_pre and flush_logs_post must return a skipped/error RefreshSkip before report rendering, manifest writes, or commits. Ensure merge._post_flush observes that skip/error path.


### FINDING_2: Postbump FinalizeResult.status must match bash STATUS vocabulary
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-dyn-bash-contract, Codex-Pragmatic, Codex-Requirements, Codex-dyn-state-plumbing, Codex-dyn-test-gate
- **Severity**: important
- **Concern**: The plan mixes bash STATUS with rebase/force-push detail tokens such as already-fresh, rebased, and *-push-skipped, which would cause parity tests to fail or bless Python-only operator-visible status drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Revise the plan so FinalizeResult.status exactly mirrors bash STATUS values: ok, rebase-failed, push-failed, remote-check-failed, branch-mismatch, postbump-cwd-not-repo, postbump-state-corrupt if covered. Put already-fresh/rebased in rebase_status and absent/skipped-repo-unavailable/pushed/noop_same_ref/failed in force_push_status.
  - From Codex-Edge: Set FinalizeResult.status from bash STATUS only; move already-fresh/rebased to rebase_status and absent/skipped-repo-unavailable/pushed/noop_same_ref to force_push_status; include postbump-state-corrupt if checkpoint parity is retained
  - From Codex-Innovation, Codex-dyn-bash-contract: Revise plan lines 32 and 86: successful postbump uses status=ok; store rebased/already-fresh in rebase_status and pushed/noop_same_ref/absent/skipped-repo-unavailable in force_push_status. Remove *-push-skipped from STATUS vocabulary.
  - From Codex-Pragmatic: Keep FinalizeResult.status to bash STATUS tokens only; put rebased/already-fresh in rebase_status and skipped-repo-unavailable/absent/pushed/noop_same_ref in force_push_status
  - From Codex-Requirements: Make FinalizeResult.status match only bash STATUS values: ok, rebase-failed, push-failed, remote-check-failed, branch-mismatch, postbump-cwd-not-repo, postbump-state-corrupt. Put rebased/already-fresh in rebase_status and absent/skipped-repo-unavailable/pushed/noop_same_ref/failed in force_push_status. Add unit and bash-parity coverage for valid legacy checkpoint clearing, unknown legacy checkpoint clearing, and corrupt or symlink checkpoint returning postbump-state-corrupt.
  - From Codex-dyn-state-plumbing: Pin result.status to bash STATUS only: ok, rebase-failed, push-failed, remote-check-failed, branch-mismatch, postbump-cwd-not-repo, or state-corrupt tokens. Put already-fresh/rebased in rebase_status and skipped-repo-unavailable/absent/pushed/noop_same_ref in force_push_status.
  - From Codex-dyn-test-gate: Revise plan/tests so result.status equals bash STATUS only; assert rebased/already-fresh/absent/skipped-repo-unavailable in rebase_status or force_push_status


### FINDING_3: Local cleanup must preserve bash’s non-fatal fetch and delete semantics
- **Reviewer(s)**: Cursor-Edge, Codex-dyn-test-gate
- **Severity**: important
- **Concern**: The plan does not fully pin bash local-cleanup behavior: exhausted origin/main fetch retries remain non-fatal, only checkout/pull failures mark partial and skip branch delete, branch-delete failure does not make cleanup partial, and larch-log reset behavior needs dangerous branch coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: State explicitly: after fetch retry failure continue (match bash); only checkout or pull --ff-only failure sets partial and skips branch delete
  - From Codex-dyn-test-gate: Add minimal _local_cleanup fixtures for checkout/pull failure => partial and no delete, delete failure => cleanup_success true/local status success with BRANCH_DELETED=false, larch-only flush ahead => reset, and mixed diff/non-flush subject => no reset


### FINDING_4: Postmerge flush must not be suppressed by local cleanup partial
- **Reviewer(s)**: Codex-Edge, Codex-Innovation
- **Severity**: important
- **Concern**: The plan can be read to gate postmerge manifest/report finalization on local_cleanup_status=partial, while bash still finalizes postmerge run logs when the PR is closed even if local cleanup partially fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Do not gate postmerge flush on local_cleanup_status=partial; gate on post.outcome OK plus run_id/pr_number/repo_available/pr_closed, and keep recovery failure as a report/manifest skip rather than a local-cleanup skip
  - From Codex-Innovation: Clarify plan line 43: local_cleanup_status=partial still permits postmerge manifest finalization when ctx.pr_closed is true. Only non-OK finalize results or recovery/write failures should suppress the report/write path.


### FINDING_5: CI-fix defer-rebase must happen after the fix commit inside stage/push flow
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Moving only push semantics or threading did_rebase through monitor/evaluate_failure misses bash’s post-commit behind-main check and defer-push rebase inside the CI fix staging/push path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Port the post-commit behind-main check and `defer-push` rebase inside `stage_and_push`/`run_ci_fix` (mirror `scripts/ship-pr.sh:1655-1706`); keep force-push only when `did_rebase` or `CI_FIX_REBASE_PENDING`


### FINDING_6: Postbump log refresh belongs in ship.py, not finalize.postbump
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Keeping flush_logs_pre inside finalize.postbump diverges from bash layering, where ship-pr refreshes logs before finalize and implement-finalize postbump emits LOG_WRITE_STATUS=skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Move Trigger-C refresh to ship.py before finalize.postbump (mirror run_bump_phase); make postbump rebase/push-only and set log_write_status=skipped; drop flush_logs_pre from postbump
  - From Cursor-Requirements: Match bash layering: run the pre-push refresh from ship.py before postbump (like refresh-run-logs.sh), drop flush from finalize.postbump, emit LOG_WRITE_STATUS=skipped on the postbump result, or document an explicit parity boundary and exclude flush from postbump subprocess cases.


### FINDING_7: Postmerge recovery/write failures should not stall a completed merge
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan describes postmerge recovery/write failure as returning skipped/error, but bash treats the failure as warning-only after PR closure and still advances done.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: State explicitly that recovery/write failure skips final report/log flush but run_postmerge_phase still returns Outcome.OK/advances done, matching scripts/ship-pr.sh


### FINDING_8: CI_FIX_REBASE_PENDING needs explicit RunContext/state-file lifecycle
- **Reviewer(s)**: Codex-Pragmatic, Codex-dyn-state-plumbing
- **Severity**: important
- **Concern**: Persisted CI_FIX_REBASE_PENDING cannot survive a Python resume unless RunContext hydrates it, ship state serializes it, monitor/fix results pass it through, and successful push clears it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add a minimal ci_fix_rebase_pending field, hydrate it from env/state as needed, serialize it in _write_ship_state, and pass it into ci_monitor/stage_and_push so retry force-push behavior is preserved
  - From Codex-dyn-state-plumbing: Add an explicit lifecycle: read the existing CI_FIX_REBASE_PENDING state before monitor/evaluate, preserve/write it in ship-pr-state, pass it through MonitorResult/FixResult, and clear it only after the successful push path.


### FINDING_9: Verify-main must preserve bash prefix/suffix matching semantics
- **Reviewer(s)**: Cursor-dyn-bash-contract, Codex-dyn-bash-contract, Codex-dyn-test-gate
- **Severity**: important
- **Concern**: Exact subject equality for verify-main would diverge from bash, which accepts prefix matches on the expected PR title plus number and PR-number suffix fallback, including admin merge cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-bash-contract: Port `verify-main.sh` matching literally: prefix on `"$pr_title (#$pr_number)"`, then suffix fallback on `(#N)`; do not require exact `git log -1` equality.
  - From Codex-dyn-bash-contract: Port verify-main's prefix and suffix rules and either read HEAD after cleanup like bash or explicitly test any intentional main-ref divergence; add a suffix/admin parity case.
  - From Codex-dyn-test-gate: Define the verify-main match tests to include at least the PR-number suffix fallback, or state explicitly that the native check must preserve verify-main.sh prefix/suffix semantics


### FINDING_10: Postbump checkpoint handling and corrupt-state parity are missing
- **Reviewer(s)**: Codex-dyn-bash-contract, Codex-Requirements
- **Severity**: important
- **Concern**: The plan omits or under-specifies bash’s .postbump-phase checkpoint branch, including clearing valid legacy checkpoints and returning postbump-state-corrupt for symlink, oversized, or malformed checkpoint files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-bash-contract: Port read/clear checkpoint handling minimally and add parity cases for valid legacy clear and corrupt checkpoint => postbump-state-corrupt.
  - From Codex-Requirements: Make FinalizeResult.status match only bash STATUS values: ok, rebase-failed, push-failed, remote-check-failed, branch-mismatch, postbump-cwd-not-repo, postbump-state-corrupt. Put rebased/already-fresh in rebase_status and absent/skipped-repo-unavailable/pushed/noop_same_ref/failed in force_push_status. Add unit and bash-parity coverage for valid legacy checkpoint clearing, unknown legacy checkpoint clearing, and corrupt or symlink checkpoint returning postbump-state-corrupt.


### FINDING_11: Teardown recovery failure should not suppress the larch-log commit path
- **Reviewer(s)**: Codex-dyn-bash-contract
- **Severity**: important
- **Concern**: The plan says recovery_ok=false skips teardown report/commit, but bash only uses recovery failure to skip recovery/stall manifest writes; the larch-log commit still runs unless independently gated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-bash-contract: Mirror bash: no teardown final-report path, use recovery_ok only for recovery/stall manifest writes, and gate commit only on run_id, repo availability, no post-merge sentinel, and no logs-commit env.


### FINDING_12: run_postmerge_phase caller must not overwrite failed postmerge state as done
- **Reviewer(s)**: Codex-dyn-state-plumbing
- **Severity**: important
- **Concern**: Even if run_postmerge_phase returns non-OK on recovery or postmerge failure, the caller can still write phase=done with stale pre-postmerge context immediately afterward.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-state-plumbing: Gate the final phase=done write on post.outcome is OK. On non-OK, write terminal/stall state from post.status and do not overwrite it with the stale working ctx.


### FINDING_13: Bash parity fail-closed guard must be in an always-collected test module
- **Reviewer(s)**: Cursor-dyn-test-gate
- **Severity**: important
- **Concern**: A sentinel guard placed in the same module as module-level skipif can inherit broadened skips, letting make py-test pass while bash parity tests are not actually collected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-gate: Place the guard in a separate always-collected module (e.g. test_finalize_bash_parity_gate.py) that asserts skipif is bash-absence-only and that parity tests are collected when shutil.which("bash") is set


### FINDING_14: run_postmerge_phase needs Python tests for skipped-OK non-closed paths
- **Reviewer(s)**: Codex-dyn-test-gate
- **Severity**: important
- **Concern**: Finalize/parity tests alone do not prove ship.run_postmerge_phase avoids load/recover and flush for skipped OK postmerge results when the PR is not closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-test-gate: Add one python/test_ship.py run_postmerge_phase test with ctx.pr_closed=False and a skipped OK postmerge result, asserting no load_or_recover_manifest or flush_logs_post; keep the merged path asserting flush


### FINDING_15: Run-log fail-closed recovery needs an absent-run-dir fixture
- **Reviewer(s)**: Codex-dyn-test-gate
- **Severity**: important
- **Concern**: The plan changes load_or_recover_manifest behavior for a valid RUN_ID with no run directory, but proposed tests may only cover teardown stall and miss helper regressions used by ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-test-gate: post Add a small python/test_run_logs.py case for valid RUN_ID with missing larch-logs/implement/<run_id> producing partial plus recovery_reason; if recovery_ok is surfaced, also assert callers skip report/commit on recovery failure

