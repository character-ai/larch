### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:19-24
- **Concern**: Orphan flush reuse cites merge.py flush detection. Scenario: local-cleanup.sh uses origin/main..HEAD and diff from pre-fetch SHA; merge._flush_recoverable uses pr_head_oid..HEAD with ancestor and max-commit guards — wrong reset or skipped reset on main after postmerge
- **Proposed resolution**: Port local-cleanup.sh steps 3–4 literally (origin/main range, pre-fetch diff base); do not call merge._flush_recoverable

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:74
- **Concern**: forked cleanup remote contradicts bash. Scenario: Edge case says keep upstream for cleanup; local-cleanup.sh always fetch/pull origin main — forked runs diverge from bash parity tests
- **Proposed resolution**: Use origin for postmerge fetch/pull/reset; reserve upstream for postbump rebase only

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:251-307
- **Concern**: teardown() plan omits bash larch-log commit. Scenario: run_teardown 1014–1020 commits pending logs when recovery_ok and no post-merge sentinel; Python teardown has no equivalent — stalled runs lose log batches
- **Proposed resolution**: Add teardown best-effort flush_logs_post/commit path gated by recovery_ok, repo_unavailable, post-merge sentinel, and NO_LOGS_COMMIT

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ci_monitor.py:865-891
- **Concern**: CI_FIX_REBASE_PENDING scoped to stage_and_push only. Scenario: Bash persists CI_FIX_REBASE_PENDING in ship state and evaluate_failure short-circuits to push-only on next attempt (ship-pr.sh:2231); FixResult alone cannot carry state across monitor iterations
- **Proposed resolution**: Wire rebase_pending through evaluate_failure entry, ship _write_ship_state, and monitor loop; force-push in stage_and_push when pending or post-rebase

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:48-88
- **Concern**: postbump-cwd-not-repo guard missing from plan steps. Scenario: Bash returns STATUS=postbump-cwd-not-repo before rebase when cwd is not a git repo; Python postbump has no equivalent — parity tests will fail
- **Proposed resolution**: Add git rev-parse --show-toplevel guard mapping to postbump-cwd-not-repo before flush/rebase

### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/run_logs.py:323-344
- **Concern**: load_or_recover_manifest init_run cannot fail closed. Scenario: Bash larch-log init failure sets larch_recovery_ok=false and skips manifest/report; Python falls through to init_run which always writes locally — recovery_ok never surfaces on missing run tree
- **Proposed resolution**: Return recovery_ok from load_or_recover_manifest (or dedicated recovery helper) when synthesis/init fails; gate teardown commit and postmerge flush on it per bash

### FINDING_7:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/local-cleanup.sh:138-147; python/finalize.py:132-134
- **Concern**: Plan does not preserve branch-delete failure as non-fatal local-cleanup success. Scenario: Bash emits success after checkout and pull succeed even when git branch -D fails; Python may keep current partial behavior and fail parity
- **Proposed resolution**: Set cleanup_success true after checkout/fetch/pull complete; return branch_deleted=false separately; only checkout/pull failure should make partial

### FINDING_8:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/local-cleanup.sh:75-119; scripts/check-remote-branch.sh:33-57; scripts/git-force-push.sh:85-88
- **Concern**: Plan conflicts on forked remotes by saying to preserve upstream selection in cleanup and force-push. Scenario: Bash uses origin for local cleanup, remote branch checks, and force-push; using upstream could break parity or try to mutate upstream
- **Proposed resolution**: Revise the edge case: use upstream only as the rebase base; use origin for cleanup fetch/pull and all branch checks/force-pushes

### FINDING_9:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: python/ci_monitor.py:865-890; scripts/ship-pr.sh:1655-1706
- **Concern**: CI-fix plan risks unconditional force-push because stage_and_push has no did_rebase or pending input. Scenario: A normal CI-fix commit with no rebase could be force-pushed unnecessarily, broadening remote mutation compared with bash
- **Proposed resolution**: Thread did_rebase/rebase_pending into stage_and_push; keep normal git push without rebase; force-push only after rebase or pending retry

### FINDING_10:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/finalize.py:22-33; scripts/implement-finalize.sh:372-379
- **Concern**: Postbump result model still lacks REBASE_STATUS and FORCE_PUSH_STATUS parity fields. Scenario: Parity tests cannot compare bash KVs cleanly, and implementation may return status=rebased where bash emits STATUS=ok plus REBASE_STATUS=rebased
- **Proposed resolution**: Add rebase_status and force_push_status to FinalizeResult; reserve status for bash STATUS tokens like ok, rebase-failed, push-failed

### FINDING_11:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:124-134
- **Concern**: _local_cleanup step semantics omit bash early-exit and branch-delete non-fatality. Scenario: Bash local-cleanup.sh exits after checkout or pull failure without running later steps; branch delete failure still yields CLEANUP_SUCCESS=true. Current Python and the plan’s partial/success rule would still mark partial on delete failure and may run pull/delete after checkout/pull fails.
- **Proposed resolution**: State _local_cleanup like bash: return partial immediately on checkout/pull failure (skip fetch/reset/pull/delete as appropriate); set success when checkout and pull succeed regardless of branch_deleted.

### FINDING_12:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:22-33; scripts/implement-finalize.sh:372-380
- **Concern**: Postbump plan conflates bash STATUS with REBASE_STATUS/FORCE_PUSH_STATUS. Scenario: FinalizeResult only has status, but bash emits separate STATUS=ok/rebase-failed/push-failed and REBASE_STATUS=already-fresh/rebased plus FORCE_PUSH_STATUS. A parity rewrite that stores already-fresh or rebased in status cannot compare field-for-field and will preserve the current drift.
- **Proposed resolution**: Extend FinalizeResult with rebase_status, force_push_status, and log_write_status, then set status only to bash STATUS values such as ok, rebase-failed, push-failed, branch-mismatch, remote-check-failed, or postbump-cwd-not-repo.

### FINDING_13:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/finalize.py:276-345; scripts/implement-finalize.sh:412-440
- **Concern**: Postbump rebase may still invoke conflict-fixer scope. Scenario: Plan allows reusing rebase_and_push(..., defer_push=True) but does not require allow_conflict_fix=False. The helper defaults to launching conflict resolution, while bash rebase-push.sh --no-push treats conflicts as rebase-failed and bails to cleanup.
- **Proposed resolution**: Set allow_conflict_fix=False for postbump, or add a no-push rebase helper that returns failed on conflicts without launching fixer agents.

### FINDING_14:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:124-129; scripts/local-cleanup.sh:75-119
- **Concern**: Plan conflicts on postmerge cleanup remote for forked runs. Scenario: The postmerge section says to reimplement local-cleanup.sh fetch/pull origin main, but the edge-case section says preserve upstream-vs-origin selection in cleanup. Bash local-cleanup always uses origin/main; using upstream for forked postmerge would diverge from the reference and can pull/reset against the wrong tracking ref.
- **Proposed resolution**: Revise the plan to say postmerge local cleanup always uses origin/main; keep upstream selection only for postbump rebase base_remote.

### FINDING_15:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/git.py:575-632; scripts/git-force-push.sh:59-118
- **Concern**: Plan points postbump and CI to the low-level lease-push helper instead of the recovery helper. Scenario: Bash git-force-push.sh includes clean-tree guard, fetch before push, noop_same_ref recovery, and one retry. Direct git.force_push_with_lease misses those branches, so dirty worktrees, race-landed pushes, and transient lease races get different outcomes.
- **Proposed resolution**: Use git.force_push_recovery or an equivalent wrapper for postbump and CI force-push paths, and map pushed/noop_same_ref to success and dirty_worktree/diverged_retry_failed to the bash failure statuses.

### FINDING_16:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:425-431
- **Concern**: Post-merge flush treats any OK postmerge as PR closed. Scenario: Bash only flushes when state PR_CLOSED=true. Python sets pr_closed=ctx.pr_closed or post.outcome is Outcome.OK, so skipped-draft/skipped-merge-false/skipped-bail can satisfy _postmerge_should_flush and run flush_logs_post when pr_number is set.
- **Proposed resolution**: Gate flush on ctx.pr_closed (or post.status==ok after real cleanup), not post.outcome alone.

### FINDING_17:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:66-70; scripts/check-remote-branch.sh:49-70
- **Concern**: The proposed postbump remote-branch gate still allows local origin/<branch> rev-parse to participate in presence detection, but bash makes git ls-remote --exit-code --heads origin <branch> authoritative.. Scenario: A stale origin/<branch> ref can mask a deleted remote branch or transport/auth failure, so Python force-pushes or reports ok where bash would emit absent or remote-check-failed.
- **Proposed resolution**: Make the live ls-remote trichotomy authoritative; use rev-parse only after live presence is confirmed if an expected lease OID is needed.

### FINDING_18:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/git-force-push.sh:52-116; python/git.py:136-145
- **Concern**: The plan names the low-level git.force_push_with_lease helpers for postbump and CI-fix push parity, but bash uses git-force-push.sh with dirty-tree guard, fetch-before-lease, noop_same_ref recovery, and one retry.. Scenario: Direct helper calls can drop dirty changes from the pushed fix, fail races that bash treats as noop_same_ref, or miss diverged_retry_failed parity.
- **Proposed resolution**: Port a small git-force-push wrapper that returns the bash STATUS tokens and reuse it in both finalize.postbump and ci_monitor.stage_and_push.

### FINDING_19:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/implement-finalize.sh:413-415; scripts/implement-finalize.sh:480-489; scripts/implement-finalize.sh:668-688
- **Concern**: The parity-test plan says to PATH-stub leaf scripts, but implement-finalize.sh invokes those leaves through $SCRIPT_DIR, not PATH.. Scenario: The rewritten tests may accidentally exercise real repo scripts or fail to force the intended rebase, remote-check, cleanup, and verify cases, weakening the fail-closed parity gate.
- **Proposed resolution**: Either run bash from a temporary copied scripts directory containing the leaf stubs, or drop leaf stubs and drive the real leaves only through git/gh stubs.

### FINDING_20:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:271-278; scripts/implement-finalize.sh:975-1019
- **Concern**: The teardown plan covers manifest recovery but does not explicitly add bash's best-effort larch-log commit path after recovery_ok succeeds.. Scenario: A stalled or failed Python teardown with RUN_ID, repo available, and no post-merge sentinel can recover/tag the manifest but leave pending run logs uncommitted, diverging from bash before Phase 7 cutover.
- **Proposed resolution**: Add the recovery_ok, LARCH_NO_LOGS_COMMIT, and post-merge-sentinel gated commit/report step to teardown, or explicitly declare that as the only parity boundary and test it.

### FINDING_21:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:425-431
- **Concern**: Postmerge flush gate misaligned with bash PR_CLOSED semantics. Scenario: `state_ctx` sets `pr_closed=ctx.pr_closed or post.outcome is Outcome.OK`, so skipped postmerge paths (draft/merge-false/bail) with Outcome.OK can flush when bash gates on merge-time PR_CLOSED=false
- **Proposed resolution**: In `run_postmerge_phase`, gate flush on `ctx.pr_closed` only (bash `scripts/ship-pr.sh:3107`); remove the `post.outcome is Outcome.OK` OR; do not broaden flush because postmerge returned OK

### FINDING_22:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:66-69, scripts/implement-finalize.sh:478-489
- **Concern**: The proposed remote-branch check can still rely on local origin/<branch> before ls-remote. Scenario: A stale local tracking ref can make Python treat a deleted remote branch as present and force-push/recreate it, while bash check-remote-branch.sh would return absent
- **Proposed resolution**: Always run the ls-remote trichotomy for branch presence; use try_rev_parse only for optional OID/diagnostic data, never to short-circuit presence

### FINDING_23:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: python/git.py:575-641, scripts/implement-finalize.sh:489-505, python/ci_monitor.py:887
- **Concern**: The plan points postbump and CI rebase pushes at simple force-with-lease helpers instead of the existing git-force-push parity helper. Scenario: Simple force-push misses the dirty-worktree guard, prefetch, noop_same_ref recovery, and retry behavior that bash depends on
- **Proposed resolution**: Use git.force_push_recovery for postbump and CI post-rebase pushes, mapping pushed and noop_same_ref to success and other statuses to the existing failure tokens

### FINDING_24:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_finalize_bash_parity.py:19-22, scripts/test-implement-finalize.sh:127-134, scripts/test-implement-finalize.sh:389-390
- **Concern**: The proposed parity tests say to PATH-stub leaf scripts, but implement-finalize.sh invokes them via $SCRIPT_DIR. Scenario: Stubs named local-cleanup.sh, rebase-push.sh, check-remote-branch.sh, git-force-push.sh, and larch-log.sh in PATH will not intercept absolute $SCRIPT_DIR calls, so tests may run real scripts or fail to cover intended branches
- **Proposed resolution**: Copy implement-finalize.sh into a sandbox scripts directory with stub leaf scripts, matching scripts/test-implement-finalize.sh, and run that sandboxed script for bash parity tests

### FINDING_25:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:73-75; scripts/local-cleanup.sh:75-119
- **Concern**: Edge case preserves upstream-vs-origin in postmerge cleanup but bash always uses origin main. Scenario: Bash local-cleanup always fetch/pull origin main; preserving upstream in _local_cleanup would diverge on forked runs and fail parity tests
- **Proposed resolution**: State cleanup must always target origin main; limit upstream-vs-origin to postbump rebase/base-remote only

### FINDING_26:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:27,55; python/finalize.py:22-33
- **Concern**: Parity tests require REBASE_STATUS and FORCE_PUSH_STATUS KVs but FinalizeResult exposes only one status field. Scenario: Bash postbump emits STATUS plus separate REBASE_STATUS and FORCE_PUSH_STATUS; field-for-field parity assertions in test_finalize_bash_parity.py cannot be implemented as written
- **Proposed resolution**: Add rebase_status and force_push_status (and keep status as bash STATUS); wire postbump() to populate them

### FINDING_27:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:39-41,85-91; python/ci_monitor.py:865-890; python/test_ci_monitor.py
- **Concern**: CI-fix force-push parity change lacks planned test coverage. Scenario: stage_and_push could regress to plain git push or drop CI_FIX_REBASE_PENDING plumbing while make py-test stays green
- **Proposed resolution**: Add focused python/test_ci_monitor.py cases for lease force-push and pending-rebase FixResult propagation

### FINDING_28:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: plan.txt:73; python/retry.py:77-83
- **Concern**: Edge case proposes a new transient retry helper though retry.with_transient_retry already exists. Scenario: Unnecessary new abstraction inflates diff beyond minimum-change SIMPLE contract
- **Proposed resolution**: Reuse python/retry.with_transient_retry for postmerge fetch/pull instead of adding a parallel helper

### FINDING_29:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:73-75; scripts/local-cleanup.sh:73-96
- **Concern**: The plan contradicts bash parity by saying to preserve upstream-vs-origin selection in cleanup.. Scenario: Bash local-cleanup always fetches and pulls origin main. In forked runs, using upstream in Python cleanup would verify/delete after syncing the wrong remote and fail parity.
- **Proposed resolution**: Limit upstream-vs-origin preservation to rebase/base-remote paths. State that postmerge local cleanup always uses origin main.

### FINDING_30:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:27,55; python/finalize.py:20-30
- **Concern**: The plan requires comparing REBASE_STATUS and FORCE_PUSH_STATUS but does not add result fields for them.. Scenario: Bash emits STATUS=ok plus separate REBASE_STATUS and FORCE_PUSH_STATUS. Python can only return one postbump status today, so parity tests cannot compare field-for-field.
- **Proposed resolution**: Add minimal FinalizeResult fields such as rebase_status force_push_status and log_write_status. Define result.status as bash STATUS only.

### FINDING_31:
- **Reviewer(s)**: Codex-dyn-bash-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:27; scripts/implement-finalize.sh:479-487; scripts/check-remote-branch.sh:55-70
- **Concern**: Remote-branch presence is still based on local origin/<branch> before ls-remote. Scenario: Bash treats git ls-remote --heads origin <branch> as authoritative; a stale local origin/feat would make Python force-push and resurrect a deleted branch while bash emits STATE=absent and FORCE_PUSH_STATUS=absent
- **Proposed resolution**: Use ls-remote against origin heads as the source of truth; use try_rev_parse only after present if needed for lease metadata

### FINDING_32:
- **Reviewer(s)**: Codex-dyn-bash-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:74; scripts/local-cleanup.sh:75-84,115-123; scripts/git-force-push.sh:85-87,93-98
- **Concern**: The forked/upstream edge case conflicts with bash cleanup and force-push branches. Scenario: Bash local cleanup always fetches/pulls origin main, and git-force-push always refreshes origin/<branch>; preserving upstream in cleanup or force-push would break forked-target parity
- **Proposed resolution**: Limit upstream selection to the rebase base remote; keep postmerge cleanup and force-push/check-remote on origin

### FINDING_33:
- **Reviewer(s)**: Codex-dyn-bash-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:55; scripts/implement-finalize.sh:14,480,489,669,688
- **Concern**: Planned PATH stubs for leaf scripts will not intercept implement-finalize.sh helper calls. Scenario: implement-finalize.sh invokes helpers through $SCRIPT_DIR, so PATH-stubbed local-cleanup.sh, verify-main.sh, rebase-push.sh, git-force-push.sh, or larch-log.sh will be ignored; tests could still be smoke-like or accidentally run real helpers
- **Proposed resolution**: Stub only external commands such as git and gh while running the real helper scripts, or run an isolated copied scripts directory when a leaf helper must be replaced

### FINDING_34:
- **Reviewer(s)**: Codex-dyn-bash-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:55,69; python/finalize.py:22-34; scripts/implement-finalize.sh:372-379,575-580
- **Concern**: FinalizeResult lacks fields for bash postbump KVs the plan wants to compare. Scenario: Bash emits STATUS plus REBASE_STATUS and FORCE_PUSH_STATUS; a single Python status cannot preserve ok/rebase-failed and rebased/already-fresh and pushed/absent/failed at the same time
- **Proposed resolution**: Add explicit rebase_status and force_push_status result fields, plus log_write_status if LOG_WRITE_STATUS is asserted, and compare each to the bash KV separately

### FINDING_35:
- **Reviewer(s)**: Cursor-dyn-run-log-recovery
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ship.py:416-434
- **Concern**: Post-merge recovery fail-closed gate omitted from planned ship.py changes. Scenario: Bash skips status=done and write-final-report.sh when larch-log init fails; Python flush_logs_post can still write done and run the report after a failed or minimal recovery
- **Proposed resolution**: Port scripts/ship-pr.sh:3141-3174 recovery_ok semantics into run_postmerge_phase and/or flush_logs_post; add test_ship.py coverage

### FINDING_36:
- **Reviewer(s)**: Codex-dyn-run-log-recovery
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:323-344; scripts/ship-pr.sh:3107-3138; scripts/implement-finalize.sh:975-999
- **Concern**: The plan only calls out recovery tagging when synthesizing from an existing run dir, leaving the absent-run-dir fallback ambiguous. Scenario: When manifest.json is missing and the run directory is also gone, load_or_recover_manifest can still fall through to init_run without recovery_reason=manifest_lost_mid_run; postmerge/teardown then lose the forensic partial-recovery tag that bash adds for any absent manifest
- **Proposed resolution**: Make every valid-run-id missing-manifest path, including absent run_dir, create a partial manifest with recovery_reason=manifest_lost_mid_run and surface write failure to callers

### FINDING_37:
- **Reviewer(s)**: Codex-dyn-run-log-recovery
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/run_logs.py:572-608; scripts/ship-pr.sh:3141-3174
- **Concern**: The plan does not require the post-merge report path to gate report rendering on successful terminal manifest write. Scenario: Bash skips write-final-report.sh unless the recovered/final manifest update succeeds; Python flush_logs_post currently renders the final report before writing status=done/pr_number, so a manifest write failure can leave a report built from an incoherent manifest tree
- **Proposed resolution**: Reorder or gate flush_logs_post so recovery plus the status=done/pr_number manifest write succeeds before _write_final_report runs; on failure return a skipped/error result before report rendering

### FINDING_38:
- **Reviewer(s)**: Cursor-dyn-push-cleanup-safety
- **Severity**: important
- **Focus area**: security
- **Location**: python/finalize.py:19-23
- **Concern**: Postmerge orphan reset says to reuse merge.py flush detection. Scenario: merge._flush_recoverable (merge.py:362-386) uses pr_head_oid..HEAD and is_ancestor; local-cleanup.sh:87-112 uses origin/main..HEAD subjects and diff from pre_fetch_sha to HEAD. Reusing merge helpers can reset when bash would not, discarding non-log commits on main.
- **Proposed resolution**: Implement local-cleanup-specific guards in _local_cleanup: match bash subject prefix, ahead count, and diff baseline from pre_fetch_sha (capture before fetch); do not call merge._flush_recoverable.

### FINDING_39:
- **Reviewer(s)**: Codex-dyn-push-cleanup-safety
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:27; python/finalize.py:65-70; scripts/check-remote-branch.sh:55-80; scripts/implement-finalize.sh:479-520
- **Concern**: Postbump remote-branch gate can still trust a stale local origin/<branch> ref before ls-remote. Scenario: Bash uses live ls-remote trichotomy; a stale local tracking ref could make Python force-push and recreate a deleted branch or mask auth/network failure
- **Proposed resolution**: Require ls-remote --exit-code --heads origin <branch> with retry as the sole presence authority; use rev-parse only after a present probe for lease diagnostics; add stale-ref absent/error parity cases

### FINDING_40:
- **Reviewer(s)**: Codex-dyn-push-cleanup-safety
- **Severity**: important
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:73-75; scripts/local-cleanup.sh:75-119; scripts/check-remote-branch.sh:33-39; python/finalize.py:125-130
- **Concern**: The edge-case note says preserve upstream-vs-origin selection in cleanup and force-push paths, contradicting bash parity. Scenario: Forked runs could reset/pull local main against upstream/main or force-push a topic branch toward the base remote, broadening destructive behavior beyond bash
- **Proposed resolution**: Revise the note: fork mode uses upstream only as the rebase base; local cleanup fetch/pull/reset stays on origin/main, and postbump remote check/force-push targets the push remote/origin branch per bash

### FINDING_41:
- **Reviewer(s)**: Codex-dyn-push-cleanup-safety
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:39-41; python/ci_monitor.py:865-890; scripts/ship-pr.sh:1702-1705; scripts/git-push.sh:1-6
- **Concern**: CI-fix wording can be read as replacing every stage_and_push push with force-with-lease. Scenario: Bash force-pushes only when a rebase occurred or CI_FIX_REBASE_PENDING is set; forcing a normal CI-fix commit path can overwrite concurrent remote work that a plain push would reject
- **Proposed resolution**: Specify a conditional: preserve plain push for non-rebase CI fixes, and use force-with-lease only for did_rebase or rebase-pending paths with the pending state plumbed explicitly
