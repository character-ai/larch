### FINDING_1: Postmerge orphan flush must not reuse merge flush detection
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-push-cleanup-safety
- **Severity**: important
- **Concern**: The planned `_local_cleanup` orphan-reset logic may call merge flush detection whose commit range and diff baseline differ from `local-cleanup.sh`, risking skipped resets or destructive resets of non-log commits on `main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Port local-cleanup.sh steps 3–4 literally (origin/main range, pre-fetch diff base); do not call merge._flush_recoverable
  - From Cursor-dyn-push-cleanup-safety: Implement local-cleanup-specific guards in _local_cleanup: match bash subject prefix, ahead count, and diff baseline from pre_fetch_sha (capture before fetch); do not call merge._flush_recoverable.

### FINDING_2: Forked cleanup and push paths must keep bash origin semantics
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Edge, Cursor-Requirements, Codex-Requirements, Codex-dyn-bash-contract, Codex-dyn-push-cleanup-safety
- **Severity**: important
- **Concern**: The plan’s fork/upstream edge case conflicts with bash parity by allowing cleanup, branch checks, or force-pushes to use `upstream`; bash uses `origin` for local cleanup and push-remote branch operations, reserving upstream only as a postbump rebase base.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Use origin for postmerge fetch/pull/reset; reserve upstream for postbump rebase only
  - From Codex-Arch: Revise the edge case: use upstream only as the rebase base; use origin for cleanup fetch/pull and all branch checks/force-pushes
  - From Codex-Edge: Revise the plan to say postmerge local cleanup always uses origin/main; keep upstream selection only for postbump rebase base_remote.
  - From Cursor-Requirements: State cleanup must always target origin main; limit upstream-vs-origin to postbump rebase/base-remote only
  - From Codex-Requirements: Limit upstream-vs-origin preservation to rebase/base-remote paths. State that postmerge local cleanup always uses origin main.
  - From Codex-dyn-bash-contract: Limit upstream selection to the rebase base remote; keep postmerge cleanup and force-push/check-remote on origin
  - From Codex-dyn-push-cleanup-safety: Revise the note: fork mode uses upstream only as the rebase base; local cleanup fetch/pull/reset stays on origin/main, and postbump remote check/force-push targets the push remote/origin branch per bash

### FINDING_3: Teardown omits bash best-effort larch-log commit path
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation
- **Severity**: important
- **Concern**: Python teardown recovery may recover or tag manifests but not perform bash’s gated best-effort log commit/report step, causing stalled runs to leave pending log batches uncommitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add teardown best-effort flush_logs_post/commit path gated by recovery_ok, repo_unavailable, post-merge sentinel, and NO_LOGS_COMMIT
  - From Codex-Innovation: Add the recovery_ok, LARCH_NO_LOGS_COMMIT, and post-merge-sentinel gated commit/report step to teardown, or explicitly declare that as the only parity boundary and test it.

### FINDING_4: CI-fix rebase-pending state and force-push semantics are under-specified
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Requirements, Codex-Requirements, Codex-dyn-push-cleanup-safety
- **Severity**: important
- **Concern**: CI-fix handling does not clearly persist and thread `CI_FIX_REBASE_PENDING` across monitor iterations or condition force-with-lease on actual rebase/pending state, risking lost push-only retries, unconditional force-pushes, or untested regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Wire rebase_pending through evaluate_failure entry, ship _write_ship_state, and monitor loop; force-push in stage_and_push when pending or post-rebase
  - From Codex-Arch: Thread did_rebase/rebase_pending into stage_and_push; keep normal git push without rebase; force-push only after rebase or pending retry
  - From Cursor-Requirements, Codex-Requirements: Add focused python/test_ci_monitor.py cases for lease force-push and pending-rebase FixResult propagation
  - From Codex-dyn-push-cleanup-safety: Specify a conditional: preserve plain push for non-rebase CI fixes, and use force-with-lease only for did_rebase or rebase-pending paths with the pending state plumbed explicitly

### FINDING_5: Postbump missing cwd-not-repo guard
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Python postbump lacks the bash guard that returns `postbump-cwd-not-repo` before rebase when the current directory is not inside a git repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add git rev-parse --show-toplevel guard mapping to postbump-cwd-not-repo before flush/rebase

### FINDING_6: Run-log recovery and postmerge report paths do not fail closed
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-run-log-recovery, Codex-dyn-run-log-recovery
- **Severity**: important
- **Concern**: Manifest recovery can fall through to local initialization or continue to final report/status writes after failed or partial recovery, including absent run directories, losing bash’s `recovery_ok` semantics and forensic recovery tagging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Return recovery_ok from load_or_recover_manifest (or dedicated recovery helper) when synthesis/init fails; gate teardown commit and postmerge flush on it per bash
  - From Cursor-dyn-run-log-recovery: Port scripts/ship-pr.sh:3141-3174 recovery_ok semantics into run_postmerge_phase and/or flush_logs_post; add test_ship.py coverage
  - From Codex-dyn-run-log-recovery: Make every valid-run-id missing-manifest path, including absent run_dir, create a partial manifest with recovery_reason=manifest_lost_mid_run and surface write failure to callers
  - From Codex-dyn-run-log-recovery: Reorder or gate flush_logs_post so recovery plus the status=done/pr_number manifest write succeeds before _write_final_report runs; on failure return a skipped/error result before report rendering

### FINDING_7: Local cleanup must preserve bash early exits and non-fatal branch delete
- **Reviewer(s)**: Codex-Arch, Cursor-Edge
- **Severity**: important
- **Concern**: Planned `_local_cleanup` semantics may mark branch-delete failures as partial and may continue later cleanup steps after checkout or pull failures, diverging from bash’s early-exit and success rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Set cleanup_success true after checkout/fetch/pull complete; return branch_deleted=false separately; only checkout/pull failure should make partial
  - From Cursor-Edge: State _local_cleanup like bash: return partial immediately on checkout/pull failure (skip fetch/reset/pull/delete as appropriate); set success when checkout and pull succeed regardless of branch_deleted.

### FINDING_8: Postbump result model lacks separate bash status KVs
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Cursor-Requirements, Codex-Requirements, Codex-dyn-bash-contract
- **Severity**: important
- **Concern**: `FinalizeResult` still conflates bash `STATUS` with `REBASE_STATUS`, `FORCE_PUSH_STATUS`, and possibly log-write status, making field-for-field parity tests and implementation behavior ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add rebase_status and force_push_status to FinalizeResult; reserve status for bash STATUS tokens like ok, rebase-failed, push-failed
  - From Codex-Edge: Extend FinalizeResult with rebase_status, force_push_status, and log_write_status, then set status only to bash STATUS values such as ok, rebase-failed, push-failed, branch-mismatch, remote-check-failed, or postbump-cwd-not-repo.
  - From Cursor-Requirements: Add rebase_status and force_push_status (and keep status as bash STATUS); wire postbump() to populate them
  - From Codex-Requirements: Add minimal FinalizeResult fields such as rebase_status force_push_status and log_write_status. Define result.status as bash STATUS only.
  - From Codex-dyn-bash-contract: Add explicit rebase_status and force_push_status result fields, plus log_write_status if LOG_WRITE_STATUS is asserted, and compare each to the bash KV separately

### FINDING_9: Postbump rebase must not invoke conflict-fixer scope
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: Reusing the normal rebase helper for postbump could launch conflict-fixer agents on conflicts, while bash `rebase-push.sh --no-push` treats conflicts as `rebase-failed` and exits to cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Set allow_conflict_fix=False for postbump, or add a no-push rebase helper that returns failed on conflicts without launching fixer agents.

### FINDING_10: Postbump and CI force-pushes need git-force-push parity wrapper
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan points postbump and CI rebase pushes at low-level force-with-lease helpers instead of bash’s recovery helper, missing dirty-tree guards, fetch-before-lease, noop recovery, retry behavior, and bash status-token mapping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Use git.force_push_recovery or an equivalent wrapper for postbump and CI force-push paths, and map pushed/noop_same_ref to success and dirty_worktree/diverged_retry_failed to the bash failure statuses.
  - From Codex-Innovation: Port a small git-force-push wrapper that returns the bash STATUS tokens and reuse it in both finalize.postbump and ci_monitor.stage_and_push.
  - From Codex-Pragmatic: Use git.force_push_recovery for postbump and CI post-rebase pushes, mapping pushed and noop_same_ref to success and other statuses to the existing failure tokens

### FINDING_11: Postmerge flush incorrectly treats any OK postmerge as PR closed
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `run_postmerge_phase` broadens bash `PR_CLOSED` semantics by treating `Outcome.OK` as closed, so skipped draft, skipped merge-false, or skipped bail paths can flush logs when bash would not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Gate flush on ctx.pr_closed (or post.status==ok after real cleanup), not post.outcome alone.
  - From Cursor-Pragmatic: In `run_postmerge_phase`, gate flush on `ctx.pr_closed` only (bash `scripts/ship-pr.sh:3107`); remove the `post.outcome is Outcome.OK` OR; do not broaden flush because postmerge returned OK

### FINDING_12: Remote branch presence must use live ls-remote as authority
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-dyn-bash-contract, Codex-dyn-push-cleanup-safety
- **Severity**: important
- **Concern**: The postbump remote-branch gate can still let stale local `origin/<branch>` refs short-circuit live branch presence checks, causing Python to recreate deleted remote branches or mask transport/auth failures where bash would report absent or remote-check-failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Make the live ls-remote trichotomy authoritative; use rev-parse only after live presence is confirmed if an expected lease OID is needed.
  - From Codex-Pragmatic: Always run the ls-remote trichotomy for branch presence; use try_rev_parse only for optional OID/diagnostic data, never to short-circuit presence
  - From Codex-dyn-bash-contract: Use ls-remote against origin heads as the source of truth; use try_rev_parse only after present if needed for lease metadata
  - From Codex-dyn-push-cleanup-safety: Require ls-remote --exit-code --heads origin <branch> with retry as the sole presence authority; use rev-parse only after a present probe for lease diagnostics; add stale-ref absent/error parity cases

### FINDING_13: PATH-stubbed leaf scripts will not intercept $SCRIPT_DIR calls
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-dyn-bash-contract
- **Severity**: important
- **Concern**: The proposed parity tests rely on PATH stubs for helper scripts, but `implement-finalize.sh` invokes those helpers via `$SCRIPT_DIR`, so tests may accidentally run real scripts or fail to exercise intended branches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Either run bash from a temporary copied scripts directory containing the leaf stubs, or drop leaf stubs and drive the real leaves only through git/gh stubs.
  - From Codex-Pragmatic: Copy implement-finalize.sh into a sandbox scripts directory with stub leaf scripts, matching scripts/test-implement-finalize.sh, and run that sandboxed script for bash parity tests
  - From Codex-dyn-bash-contract: Stub only external commands such as git and gh while running the real helper scripts, or run an isolated copied scripts directory when a leaf helper must be replaced

### FINDING_14: Reuse existing transient retry helper
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Concern**: The plan proposes a new transient retry abstraction even though `python/retry.with_transient_retry` already exists, inflating the diff unnecessarily.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Reuse python/retry.with_transient_retry for postmerge fetch/pull instead of adding a parallel helper
