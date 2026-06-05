### FINDING_1: CI_FIX_REBASE_PENDING RunContext/state plumbing is missing
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic, Cursor-dyn-state-token-plumbing
- **Severity**: important
- **Concern**: The plan relies on `CI_FIX_REBASE_PENDING` being carried through `RunContext`, resume state, and ship-loop persistence, but does not sufficiently include `python/run_context.py` and full hydration/serialization paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/run_context.py with ci_fix_rebase_pending default false, from_env hydration (env plus read_state_kv when state_file set), and any test RunContext builders that need the field
  - From Codex-Arch: Add an UPDATED python/run_context.py subsection for the new field, default/env hydration, and resume/state plumbing; leave ship.py responsible for serialization and phase flow.
  - From Cursor-Pragmatic: Add UPDATED python/run_context.py: ci_fix_rebase_pending on RunContext, from_env hydration, and read via run_logs.read_state_kv when state_file is set
  - From Cursor-dyn-state-token-plumbing: Plan adds RunContext.ci_fix_rebase_pending and _write_ship_state serialization but Python never hydrates the flag from ctx.state_file at run_ship entry (bash _ci_fix_pending_hydrate at ship-pr.sh:3248) and _write_ship_state omits CI_FIX_REBASE_PENDING today; the CI loop also does not write back pending state after monitor/fix attempts A named run_ship startup helper: read CI_FIX_REBASE_PENDING from ctx.state_file when present; add the field to _write_ship_state; after each monitor/evaluate_failure path that sets or clears pending, update working via with_() and persist before the next iteration

### FINDING_2: New run-log recovery skip reasons are not propagated through merge post-flush
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan changes `run_logs.flush_logs_post` to fail closed on recovery/manifest failures, but omits the corresponding `python/merge.py` behavior, so `merge_pr(..., post_flush=True)` can silently swallow new skipped reasons.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add an UPDATED python/merge.py step that maps the new recovery/manifest failure skip reason to MERGE_RESULT_ERROR or otherwise propagates it, with focused test_merge.py coverage. Keep ship.py postmerge warning-only behavior separate.
  - From Codex-Pragmatic: Add an UPDATED python/merge.py step requiring _post_flush to route through the centralized postmerge helper or treat recovery-failed RefreshSkip as the same merge error/warning behavior intended by the plan

### FINDING_3: Trigger-C pre-postbump refresh must remain best-effort
- **Reviewer(s)**: Cursor-Edge, Codex-Requirements
- **Severity**: important
- **Concern**: Moving the pre-postbump run-log refresh into Python risks making refresh skips or failures fatal, while bash treats that refresh as warning-only and continues into postbump.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Call `flush_logs_pre` (or equivalent) before `finalize.postbump`, log/ignore skips and commit failures, and never stall the bump phase on refresh outcome; add a `test_ship.py` case that refresh failure still reaches postbump with `log_write_status=skipped`.
  - From Codex-Requirements: Add to the plan that the pre-postbump refresh is warning-only and must not change postbump outcome; add a test where flush_logs_pre returns skipped/error and finalize.postbump still runs

### FINDING_4: Trigger-C refresh can run before branch/protected-branch validation
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: The planned Trigger-C refresh occurs before `finalize.postbump` branch guards, so Python may commit run-log artifacts on a wrong checkout or protected default branch where bash would guard first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add a ship.py preflight equivalent before Trigger-C refresh, or split finalize.postbump branch/cwd validation into a callable used before refresh; add tests that wrong branch and non-forked main/master perform no run-log refresh/commit.

### FINDING_5: Postmerge sentinel creation is not gated on PR_CLOSED
- **Reviewer(s)**: Codex-Edge, Codex-dyn-run-log-recovery
- **Severity**: important
- **Concern**: `run_postmerge_phase` can still write the post-merge sentinel when `ctx.pr_closed` is false, causing teardown to skip best-effort larch-log commits even though no merge happened.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Gate or move sentinel creation so it only happens when ctx.pr_closed is true after a terminal merge result, and extend the planned ctx.pr_closed=false postmerge test to assert no sentinel.
  - From Codex-dyn-run-log-recovery: Move or gate sentinel creation so it only happens when ctx.pr_closed is true, matching bash where the sentinel is written only after PR_CLOSED=true before advancing to postmerge, and add the skipped-OK test assertion that no sentinel is created

### FINDING_6: Postbump edge case preserves non-bash `*-push-skipped` statuses
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-bash-parity-auditor
- **Severity**: important
- **Concern**: The plan conflicts with its own bash STATUS contract by saying postbump should keep emitting `*-push-skipped`, while bash reports `STATUS=ok` and carries skip detail in `FORCE_PUSH_STATUS`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Rewrite the edge case to say result.status=ok with force_push_status=skipped-repo-unavailable or absent, matching bash.
  - From Codex-dyn-bash-parity-auditor: Remove *-push-skipped from the edge case. Require result.status=ok with force_push_status=absent or skipped-repo-unavailable and log_write_status=skipped.

### FINDING_7: Postbump failure statuses may not stall the ship flow
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan defines postbump failure status strings but does not require them to map to a stalled outcome, allowing Python to proceed to PR creation after failed rebase or push.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Specify that postbump failure statuses map to Outcome.STALLED or that ship.run inspects those statuses; add a test_ship case that a failing postbump status writes terminal state and does not enter pr-create

### FINDING_8: Teardown omits execution-issues safety-net flush
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Concern**: Python teardown parity omits bash’s safety-net flush for new `execution-issues.md` content before recovery and larch-log commit, risking lost teardown logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a narrow teardown step/helper that mirrors flush_execution_issues_safety_net before recovery/commit, plus unit or bash-parity coverage for unflushed execution-issues.md

### FINDING_9: No-push rebase parity is underspecified
- **Reviewer(s)**: Codex-dyn-bash-parity-auditor
- **Severity**: important
- **Concern**: The plan allows existing Python rebase behavior for no-push flows, but bash retries fetch and aborts conflicts; Python may differ on transient fetch failures or leave an in-progress rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-bash-parity-auditor: Add explicit no-push rebase wrapper requirements: retry git fetch with with_transient_retry, map failures to rebase-failed, and run git rebase --abort before returning on conflict.

### FINDING_10: Teardown larch-log commit lacks bash default-branch/sentinel refusals
- **Reviewer(s)**: Codex-dyn-bash-parity-auditor
- **Severity**: important
- **Concern**: The teardown commit plan lists only outer gates, but bash’s larch-log commit path also refuses default-branch/main commits and post-merge sentinel cases; Python `_larch_log_commit` lacks the same default-branch guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-bash-parity-auditor: Require teardown to call a larch-log commit parity wrapper or add the same current_branch_is_default and sentinel refusals before using _larch_log_commit.

### FINDING_11: Protected-branch refusal status violates planned bash status vocabulary
- **Reviewer(s)**: Codex-dyn-state-token-plumbing
- **Severity**: important
- **Concern**: The plan preserves a protected-branch guard, but its allowed postbump STATUS list excludes `branch-protected`, so keeping that result status would violate the stated status contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-state-token-plumbing: Map protected-branch refusal to an allowed bash STATUS such as branch-mismatch and put the protected-branch detail in detail or auxiliary fields
