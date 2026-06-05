### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:589-608
- **Concern**: Postmerge plan requires status=done/pr_number manifest write before _write_final_report, but flush_logs_post renders the report first. Scenario: Recovery or manifest write can fail after summary-final.md is already updated; bash ship-pr.sh:3146-3173 skips report on manifest failure
- **Proposed resolution**: Add flush_logs_post reorder (or a postmerge-only helper) to the plan under python/run_logs.py; write manifest before _write_final_report

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-finalize.sh:524-581
- **Concern**: Postbump status vocabulary in the plan conflicts with bash STATUS. Scenario: Plan says FinalizeResult.status may be already-fresh or rebased with push-skipped suffixes, but bash emits STATUS=ok for successful rebase plus force-push gate and puts freshness in REBASE_STATUS and push state in FORCE_PUSH_STATUS. Field-for-field parity tests would fail or encode non-bash operator status.
- **Proposed resolution**: Revise the plan so FinalizeResult.status exactly mirrors bash STATUS values: ok, rebase-failed, push-failed, remote-check-failed, branch-mismatch, postbump-cwd-not-repo, postbump-state-corrupt if covered. Put already-fresh/rebased in rebase_status and absent/skipped-repo-unavailable/pushed/noop_same_ref/failed in force_push_status.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:572-608
- **Concern**: Postmerge report/write ordering is assigned to ship.py but the side effect lives inside flush_logs_post. Scenario: The plan requires recovery and status=done/pr_number manifest write to succeed before _write_final_report runs, but run_logs.flush_logs_post currently renders the final report before writing the manifest. Keeping this helper unchanged means a ship.py-only gate cannot enforce the proposed fail-closed ordering once flush_logs_post is called.
- **Proposed resolution**: Add an explicit run_logs.py step to refactor flush_logs_post or add a narrow helper so recovery plus manifest write happens before _write_final_report/_render_* calls, and have ship.py call that path.

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/local-cleanup.sh:79-85
- **Concern**: Plan omits that origin/main fetch failure is non-fatal. Scenario: Implementer may mark local_cleanup partial or abort when fetch retries exhaust; bash warns, still runs orphan reset and pull, and only pull failure yields partial with branch delete skipped
- **Proposed resolution**: State explicitly: after fetch retry failure continue (match bash); only checkout or pull --ff-only failure sets partial and skips branch delete

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:43-82; scripts/implement-finalize.sh:372-380,524-580; plan.txt:31-32,86
- **Concern**: Postbump STATUS mapping in the plan keeps current Python already-fresh/rebased-push-skipped values even though bash STATUS is ok/rebase-failed/push-failed/remote-check-failed/branch-mismatch/postbump-cwd-not-repo/postbump-state-corrupt. Scenario: Remote-absent or repo-unavailable postbump paths would still emit non-bash status tokens, so the planned parity tests either fail or miss operator-visible drift before Python cutover
- **Proposed resolution**: Set FinalizeResult.status from bash STATUS only; move already-fresh/rebased to rebase_status and absent/skipped-repo-unavailable/pushed/noop_same_ref to force_push_status; include postbump-state-corrupt if checkpoint parity is retained

### FINDING_6:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ship.py:416-435; scripts/ship-pr.sh:3110-3176; plan.txt:43-44
- **Concern**: The plan says failed/partial postmerge cannot trigger flush, but bash still runs postmerge manifest/report work when PR_CLOSED=true even if LOCAL_CLEANUP_STATUS=partial. Scenario: A merged PR with local cleanup pull/delete failure could leave the Python run manifest partial and skip the final summary despite bash advancing done
- **Proposed resolution**: Do not gate postmerge flush on local_cleanup_status=partial; gate on post.outcome OK plus run_id/pr_number/repo_available/pr_closed, and keep recovery failure as a report/manifest skip rather than a local-cleanup skip

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/ci_monitor.py:865-891
- **Concern**: CI-fix defer-rebase lives in bash `_stage_and_push_ci_fixes` after the fix commit, not in `evaluate_failure`. Scenario: Plan only changes `stage_and_push` push semantics and threads `did_rebase` through `evaluate_failure`/monitor; Python can still plain-push a fix commit that bash would rebase onto `origin/main` first, then force-push
- **Proposed resolution**: Port the post-commit behind-main check and `defer-push` rebase inside `stage_and_push`/`run_ci_fix` (mirror `scripts/ship-pr.sh:1655-1706`); keep force-push only when `did_rebase` or `CI_FIX_REBASE_PENDING`

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-bash-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-finalize.sh:372-379,524-582
- **Concern**: Plan keeps rebased/already-fresh and *-push-skipped as FinalizeResult.status tokens, but bash emits STATUS=ok for successful postbump and puts rebase/push details in REBASE_STATUS/FORCE_PUSH_STATUS.. Scenario: Parity tests keyed on STATUS will either fail or bless current Python-only statuses; repo-unavailable or missing remote branches would report *-push-skipped instead of ok with FORCE_PUSH_STATUS=skipped-repo-unavailable/absent.
- **Proposed resolution**: Revise plan lines 32 and 86: successful postbump uses status=ok; store rebased/already-fresh in rebase_status and pushed/noop_same_ref/absent/skipped-repo-unavailable in force_push_status. Remove *-push-skipped from STATUS vocabulary.

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:3107-3175
- **Concern**: Plan says failed/partial postmerge cannot trigger a flush, which can be read to block the done-manifest/report path on local cleanup partial. Bash gates postmerge flush on PR_CLOSED, run id, PR number, and repo availability; local cleanup partial does not suppress it.. Scenario: After a real merge, a local branch delete or pull cleanup problem could leave the run log unfinalized even though the PR is closed.
- **Proposed resolution**: Clarify plan line 43: local_cleanup_status=partial still permits postmerge manifest finalization when ctx.pr_closed is true. Only non-OK finalize results or recovery/write failures should suppress the report/write path.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/finalize.py:62-64
- **Concern**: Plan keeps flush_logs_pre inside postbump while bash implement-finalize postbump always emits LOG_WRITE_STATUS=skipped and ship-pr runs refresh-run-logs.sh before finalize (scripts/ship-pr.sh:1117-1125, scripts/implement-finalize.sh:526-527). Scenario: Parity tests asserting LOG_WRITE_STATUS and subprocess KV equality fail or force a second pre-PR log commit diverging from bash
- **Proposed resolution**: Move Trigger-C refresh to ship.py before finalize.postbump (mirror run_bump_phase); make postbump rebase/push-only and set log_write_status=skipped; drop flush_logs_pre from postbump

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:48-88; plan.txt:32
- **Concern**: Plan mixes bash STATUS with REBASE_STATUS tokens for postbump. Scenario: Bash emits STATUS=ok on successful postbump and puts rebased/already-fresh in REBASE_STATUS; carrying rebased or already-fresh in FinalizeResult.status will fail parity and change operator-visible state
- **Proposed resolution**: Keep FinalizeResult.status to bash STATUS tokens only; put rebased/already-fresh in rebase_status and skipped-repo-unavailable/absent/pushed/noop_same_ref in force_push_status

### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ship.py:416-443; plan.txt:44
- **Concern**: Postmerge recovery/write failure is described as returning a skipped/error result, but bash treats it as warning-only. Scenario: If manifest recovery or status=done write fails after the PR is closed, Python could stall/error a completed merge while bash records a warning and advances to done
- **Proposed resolution**: State explicitly that recovery/write failure skips final report/log flush but run_postmerge_phase still returns Outcome.OK/advances done, matching scripts/ship-pr.sh

### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_context.py:27-67, python/ship.py:352-392; plan.txt:48
- **Concern**: CI_FIX_REBASE_PENDING persistence lacks a concrete RunContext/state-file update target. Scenario: The proposed persisted retry cannot survive a Python resume because RunContext.from_env does not hydrate CI_FIX_REBASE_PENDING and _write_ship_state does not serialize it
- **Proposed resolution**: Add a minimal ci_fix_rebase_pending field, hydrate it from env/state as needed, serialize it in _write_ship_state, and pass it into ci_monitor/stage_and_push so retry force-push behavior is preserved

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:27-34; python/finalize.py:62-64; scripts/ship-pr.sh:1117-1125
- **Concern**: Postbump keeps inline flush_logs_pre while parity tests target the bash postbump subcommand alone. Scenario: The plan preserves flush_logs_pre inside finalize.postbump and requires field-for-field parity against bash implement-finalize postbump, but bash postbump never flushes logs (LOG_WRITE_STATUS stays skipped; refresh-run-logs.sh runs in ship-pr.sh first). Side-by-side parity cases will diverge on flush side effects and log-refresh failure statuses.
- **Proposed resolution**: Match bash layering: run the pre-push refresh from ship.py before postbump (like refresh-run-logs.sh), drop flush from finalize.postbump, emit LOG_WRITE_STATUS=skipped on the postbump result, or document an explicit parity boundary and exclude flush from postbump subprocess cases.

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py; scripts/implement-finalize.sh:544-580; plan.txt:32,53,67,86
- **Concern**: Postbump status plan still drifts from bash STATUS tokens. Scenario: The plan says result.status is bash-only but includes rebased/already-fresh and *-push-skipped, while bash emits STATUS=ok for successful rebase plus absent/repo-unavailable force-push gate; it also omits the corrupt .postbump-phase path that emits STATUS=postbump-state-corrupt. Parity tests could pass with Python-only status drift and miss the symlink/corrupt checkpoint fail-closed branch.
- **Proposed resolution**: Make FinalizeResult.status match only bash STATUS values: ok, rebase-failed, push-failed, remote-check-failed, branch-mismatch, postbump-cwd-not-repo, postbump-state-corrupt. Put rebased/already-fresh in rebase_status and absent/skipped-repo-unavailable/pushed/noop_same_ref/failed in force_push_status. Add unit and bash-parity coverage for valid legacy checkpoint clearing, unknown legacy checkpoint clearing, and corrupt or symlink checkpoint returning postbump-state-corrupt.

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-bash-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/plan.txt:26-27 / scripts/verify-main.sh:75-91
- **Concern**: Postmerge verify step mixes exact title equality with “align to verify-main.sh”. Scenario: bash `verify-main.sh` verifies via prefix match on the full expected title and a `(#N)` suffix fallback for `--admin` merges, not strict equality. Following the plan’s equality wording would mark valid admin merges `unexpected` and fail parity tests.
- **Proposed resolution**: Port `verify-main.sh` matching literally: prefix on `"$pr_title (#$pr_number)"`, then suffix fallback on `(#N)`; do not require exact `git log -1` equality.

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-bash-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/verify-main.sh:75-90, scripts/implement-finalize.sh:686-700
- **Concern**: Plan says to compare git log -1 --format=%s main exactly to the expected title, but bash verify-main checks current HEAD after cleanup and accepts prefix match plus PR-number suffix fallback.. Scenario: Admin merge subjects ending in (#N), or cleanup partial paths that leave HEAD off main, would produce Python VERIFY_MAIN_STATUS values that differ from bash.
- **Proposed resolution**: Port verify-main's prefix and suffix rules and either read HEAD after cleanup like bash or explicitly test any intentional main-ref divergence; add a suffix/admin parity case.

### FINDING_18:
- **Reviewer(s)**: Codex-dyn-bash-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-finalize.sh:343-365, scripts/implement-finalize.sh:544-558
- **Concern**: Plan omits the postbump checkpoint branch from implementation and parity coverage.. Scenario: Bash clears valid legacy .postbump-phase files but emits STATUS=postbump-state-corrupt for symlink, oversized, or malformed checkpoint files; Python could miss that observable branch.
- **Proposed resolution**: Port read/clear checkpoint handling minimally and add parity cases for valid legacy clear and corrupt checkpoint => postbump-state-corrupt.

### FINDING_19:
- **Reviewer(s)**: Codex-dyn-bash-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/implement-finalize.sh:975-1020
- **Concern**: Plan says recovery_ok=false skips teardown report/commit, but bash only uses larch_recovery_ok to skip recovery/stall manifest writes; the larch-log commit still runs unless LARCH_NO_LOGS_COMMIT is true or the post-merge sentinel exists.. Scenario: On missing-manifest recovery failure, proposed Python would skip a teardown commit that bash still attempts, changing failure behavior and log preservation.
- **Proposed resolution**: Mirror bash: no teardown final-report path, use recovery_ok only for recovery/stall manifest writes, and gate commit only on run_id, repo availability, no post-merge sentinel, and no logs-commit env.

### FINDING_20:
- **Reviewer(s)**: Cursor-dyn-state-plumbing
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:572-609
- **Concern**: Plan adds recovery_ok to load_or_recover_manifest but only names ship.run_postmerge_phase and finalize.teardown as callers that must skip on failure. Scenario: flush_logs_post (and flush_logs_pre/update_manifest) still call load_or_recover_manifest internally and can render _write_final_report and write status=done after a failed recovery when ship's outer gate is bypassed (merge.py:155) or via the second load inside run_postmerge_phase (ship.py:432-433)
- **Proposed resolution**: In run_logs.py extend the UPDATED section: flush_logs_post must fail-closed (RefreshSkip or no done write) when recovery_ok is false; apply the same rule to flush_logs_pre and update_manifest or document a single internal helper all paths use

### FINDING_21:
- **Reviewer(s)**: Codex-dyn-state-plumbing
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:657-666
- **Concern**: F1 postmerge failure can still be persisted as done. Scenario: The plan makes run_postmerge_phase return an error on recovery or postmerge failure, but the caller unconditionally writes phase done with the pre-postmerge ctx immediately afterward. A recovery/write failure can leave ship-pr-state showing done/closed while the returned outcome is stalled.
- **Proposed resolution**: Gate the final phase=done write on post.outcome is OK. On non-OK, write terminal/stall state from post.status and do not overwrite it with the stale working ctx.

### FINDING_22:
- **Reviewer(s)**: Codex-dyn-state-plumbing
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_context.py:27-67; python/ship.py:352-392; python/ci_monitor.py:1059-1280
- **Concern**: F2 persisted CI_FIX_REBASE_PENDING has no explicit hydrate path. Scenario: The plan says to thread rebase_pending through ci_monitor and ship-state writing, but current RunContext has no field for CI_FIX_REBASE_PENDING and _write_ship_state omits it. A resumed Python run can lose the pending force-push retry before evaluate_failure sees it.
- **Proposed resolution**: Add an explicit lifecycle: read the existing CI_FIX_REBASE_PENDING state before monitor/evaluate, preserve/write it in ship-pr-state, pass it through MonitorResult/FixResult, and clear it only after the successful push path.

### FINDING_23:
- **Reviewer(s)**: Codex-dyn-state-plumbing
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:48-88; scripts/implement-finalize.sh:524-581
- **Concern**: F3 postbump status vocabulary is internally inconsistent. Scenario: The plan says result.status is reserved for bash STATUS tokens, but also lists already-fresh/rebased and -push-skipped as result.status values. In bash those belong to REBASE_STATUS/FORCE_PUSH_STATUS, while STATUS is ok on successful postbump.
- **Proposed resolution**: Pin result.status to bash STATUS only: ok, rebase-failed, push-failed, remote-check-failed, branch-mismatch, postbump-cwd-not-repo, or state-corrupt tokens. Put already-fresh/rebased in rebase_status and skipped-repo-unavailable/absent/pushed/noop_same_ref in force_push_status.

### FINDING_24:
- **Reviewer(s)**: Codex-dyn-state-plumbing
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/run_logs.py:526-609; python/merge.py:149-170
- **Concern**: F4 recovery_ok is not specified for all run_logs callers. Scenario: The plan surfaces recovery_ok for finalize.teardown and ship.run_postmerge_phase, but load_or_recover_manifest also feeds flush_logs_pre/flush_logs_post and merge._post_flush. If recovery failure is handled only in ship/finalize, these callers can still render reports or write manifests after failed recovery.
- **Proposed resolution**: Centralize fail-closed handling in run_logs: when recovery_ok is false, flush_logs_pre and flush_logs_post must return a skipped/error RefreshSkip before report rendering, manifest writes, or commits. Ensure merge._post_flush observes that skip/error path.

### FINDING_25:
- **Reviewer(s)**: Cursor-dyn-test-gate
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_finalize_bash_parity.py:64-68
- **Concern**: Fail-closed guard colocated with module-level skipif. Scenario: A sentinel test in the same module inherits pytestmark; any broadened skipif (e.g. re-adding script-exists) skips the guard too, so make py-test stays green while parity never runs under bash
- **Proposed resolution**: Place the guard in a separate always-collected module (e.g. test_finalize_bash_parity_gate.py) that asserts skipif is bash-absence-only and that parity tests are collected when shutil.which("bash") is set

### FINDING_26:
- **Reviewer(s)**: Codex-dyn-test-gate
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:32,86; scripts/implement-finalize.sh:372-378,461-522,562-580
- **Concern**: Postbump status contract mixes bash STATUS with Python legacy statuses. Scenario: Parity tests that compare result.status to bash STATUS will fail or encode drift if implementation follows the plan and returns rebased/already-fresh/*-push-skipped; bash emits STATUS=ok for successful rebase plus force gate, with rebase details in REBASE_STATUS/FORCE_PUSH_STATUS
- **Proposed resolution**: Revise plan/tests so result.status equals bash STATUS only; assert rebased/already-fresh/absent/skipped-repo-unavailable in rebase_status or force_push_status

### FINDING_27:
- **Reviewer(s)**: Codex-dyn-test-gate
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:19-25,52-56,62-67; scripts/local-cleanup.sh:87-147; scripts/implement-finalize.sh:668-683
- **Concern**: Local-cleanup tests do not pin the dangerous branches. Scenario: A branch-delete failure could be treated as partial, or the orphan larch-log reset could use the wrong baseline and drop non-log commits; the proposed tests only say branch-delete success/partial and cleanup success/partial
- **Proposed resolution**: Add minimal _local_cleanup fixtures for checkout/pull failure => partial and no delete, delete failure => cleanup_success true/local status success with BRANCH_DELETED=false, larch-only flush ahead => reset, and mixed diff/non-flush subject => no reset

### FINDING_28:
- **Reviewer(s)**: Codex-dyn-test-gate
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:41-44,58-68,98-102; python/ship.py:416-433; python/test_ship.py:85-176
- **Concern**: Postmerge flush gate change has no proposed Python test. Scenario: The listed ctx-timing bug lives in run_postmerge_phase: skipped draft/merge-false/bail postmerge results are Outcome.OK, but finalize/parity tests call finalize.postmerge directly and do not prove the ship wrapper avoids load/recover and flush
- **Proposed resolution**: Add one python/test_ship.py run_postmerge_phase test with ctx.pr_closed=False and a skipped OK postmerge result, asserting no load_or_recover_manifest or flush_logs_post; keep the merged path asserting flush

### FINDING_29:
- **Reviewer(s)**: Codex-dyn-test-gate
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:37-39,98-105; python/run_logs.py:323-344; python/test_run_logs.py:204-215,483-497
- **Concern**: Run-log fail-closed recovery lacks an absent-run-dir fixture. Scenario: load_or_recover_manifest currently falls through to init_run for a valid run id with no run directory; the plan changes that, but proposed tests only mention teardown stall and may not catch helper regressions used by ship
- **Proposed resolution**: post Add a small python/test_run_logs.py case for valid RUN_ID with missing larch-logs/implement/<run_id> producing partial plus recovery_reason; if recovery_ok is surfaced, also assert callers skip report/commit on recovery failure

### FINDING_30:
- **Reviewer(s)**: Codex-dyn-test-gate
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:26,54,64-67; scripts/verify-main.sh:75-90
- **Concern**: Verify-main tests can miss bash prefix/suffix matching. Scenario: An exact-only native check passes simple match/mismatch tests but diverges from verify-main.sh, which accepts prefix matches and PR-number suffix matches for admin merges
- **Proposed resolution**: Define the verify-main match tests to include at least the PR-number suffix fallback, or state explicitly that the native check must preserve verify-main.sh prefix/suffix semantics
