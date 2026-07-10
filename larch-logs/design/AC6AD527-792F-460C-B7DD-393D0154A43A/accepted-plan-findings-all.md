### FINDING_1: De-stall the hydrated RunContext before resumed ship writes
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Innovation, Codex-Requirements, Cursor-dyn-Ship Reentry State, Codex-dyn-Ship Reentry State
- **Severity**: major
- **Concern**: Re-entry resets need a de-stalled in-memory `RunContext`, not just a rewritten `ship-pr-state.sh`; otherwise later non-terminal writes can re-persist `STALL_TRACKING` / `STALL_STEP` and keep the resumed drive looking terminal. The first post-reset write and the pre-refresh state both need to prove the stall overlay is gone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the re-entry helper, delete finalize-state.sh when it is a regular file, then call _write_ship_state(ctx.with_(stall_tracking=False, stall_step=""), phase=<mapped in-progress label>, ...) before any flush_logs_pre
  - From Cursor-Arch: In the stalled re-entry test, assert PHASE is an in-progress label, STALL_TRACKING=false, STALL_STEP is empty, and finalize-state.sh is absent before the first pre-PR refresh runs
  - From Cursor-Innovation: In the new re-entry helper, call _write_ship_state with ctx.with_(stall_tracking=False, stall_step="") (and terminal_outcome left None). Extend test_ship.py / test_ship_state.py to seed STALL_TRACKING=true on both disk state and the ctx passed into run_ship, then assert the written ship-pr-state.sh clears stall keys before the first flush
  - From Codex-Innovation: Build the reset state from ctx.with_(stall_tracking=False, stall_step="") before calling _write_ship_state and before the first resumed flush.
  - From Cursor-Pragmatic: Have the helper return ctx.with_(stall_tracking=False, stall_step="") (and assign ctx at run_ship entry after blocked-resume handling). Use that cleared ctx for every subsequent _write_ship_state and flush. Extend the stalled re-entry test to assert STALL_TRACKING=false after the first post-reset state write, not only before refresh.
  - From Cursor-Requirements: In Fix 2, call _write_ship_state with ctx.with_(stall_tracking=False, stall_step="") (and rely on terminal-only key pops); add a re-entry test that hydrates ctx from a stalled seed and asserts STALL_TRACKING/STALL_STEP/EXIT_CODE are cleared
  - From Cursor-Requirements: Extend the stalled re-entry test to assert flush_logs_pre is not skipped for preterminal reason and that _flush_guideline_outcome_before_pr does not raise after de-terminalize (monkeypatch or hermetic git as needed)
  - From Codex-Requirements: Have the reset helper return or install a ctx with stall_tracking=False and stall_step="" for all subsequent hydration and _write_ship_state calls after it deletes or neutralizes finalize-state.sh. Assert the pre-refresh state file has STALL_TRACKING=false and blank STALL_STEP.
  - From Cursor-dyn-Ship Reentry State: In the de-terminalization helper (ship.py after blocked-resume handling), call _write_ship_state with ctx.with_(stall_tracking=False, stall_step="") (optionally after _hydrate_resume_context). Extend the re-entry test to assert STALL_TRACKING=false and empty STALL_STEP in ship-pr-state.sh before the first flush_logs_pre.
  - From Codex-dyn-Ship Reentry State: Have the helper return or construct a de-stalled RunContext and use it for every resumed _write_ship_state, for example ctx.with_(stall_tracking=False, stall_step=''), before any branch-specific state write.


### FINDING_2: Keep the reset after merged/done recovery branches
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Resetting too early can clear the stalled overlay before the merged/done recovery path has a chance to repair the committed summary, so the recovery branch loses the very signal it needs to reconcile.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Restrict the reset to the pre-PR resume starts only, or move it to after the merged/done reconciliation branches have finished.


### FINDING_3: Add an explicit matcher for REFRESH_SKIP_PRETERMINAL_OUTCOME
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Requirements, Cursor-dyn-Ship Reentry State
- **Severity**: major
- **Concern**: The new preterminal refresh-skip reason needs explicit classifier routing; otherwise it can fall through or be misrouted, and the resume hint / failure-class behavior becomes ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add a focused classify test (CLI or unit) where evidence contains the new reason and STALL_STEP=pr-create-guideline-outcome-refresh, and assert FAILURE_CLASS=transient-infra with RESUME_HINT=step8-shippr; implement an explicit matcher in _classify_text for the new reason rather than relying on phase fallback
  - From Codex-Innovation: Add a narrow _classify_text branch (or DIRECT_BAIL-style map) keyed on the new reason token and/or stall_step pr-create-guideline-outcome-refresh that preserves FAILURE_CLASS=transient-infra and RESUME_HINT=step8-shippr; add a classifier unit test for the new detail string.
  - From Cursor-Requirements: Limit step8-shippr to hook/commit failures (commit-failed with pre-commit hook output); route REFRESH_SKIP_PRETERMINAL_OUTCOME at pr-create-* refresh steps to unrecoverable/none; add a classify test for the new reason string
  - From Cursor-dyn-Ship Reentry State: Add a narrow _classify_text branch (or DIRECT_BAIL-style map) keyed on the new reason token and/or stall_step pr-create-guideline-outcome-refresh that preserves FAILURE_CLASS=transient-infra and RESUME_HINT=step8-shippr; add a classifier unit test for the new detail string.


### FINDING_4: Retry only the post-copy commit tail
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The retry should re-enter at the add/diff/commit tail only; re-running copy/scrub on the second attempt would wipe hook fixes from the worktree and reproduce the original stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Factor only the post-copy add/diff/commit tail into the helper; keep copy, scrub, volatile-only detection, and breadcrumb publish outside the retried block, and add a hermetic test that fails if a second copy runs between attempts


### FINDING_5: Surface the second-failure workaround
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Concern**: When the retried commit still fails, the surfaced detail needs the checking-only-hook workaround too, not just the fixer-hook shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Broaden the detector to include non-modifying pre-commit failure output used by checking hooks, not just files-were-modified output. Keep the checking-only test non-modifying and assert exactly two commit invocations plus the remedy.


### FINDING_1: Finalize-state reset can leave terminal residue
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The re-entry reset around `finalize-state.sh` can leave terminal state behind or fail open on non-regular finalize files, so the resumed drive still normalizes to `stalled`/`bailed` and can loop back into the pre-terminal refresh deadlock.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: If re-entry cannot unlink finalize-state.sh and falls back to rewriting only STALL_TRACKING=false, PHASE/EXIT_CODE/BAIL_REASON can still make the resumed drive normalize to stalled or bailed. Delete finalize-state.sh on re-entry, or rewrite the full neutral mid-flight shape and clear every terminal-overlay key.
  - From Cursor-Innovation: On refused finalize deletion, fail closed: raise `Stalled` (or return a terminal `ShipResult`) and do not call `flush_logs_pre`; add a focused ship re-entry test with a symlinked finalize overlay asserting the drive stalls instead of looping on pre-terminal refresh.


### FINDING_2: Refresh-stall detail can be misclassified as lint failure
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The new pre-terminal refresh skip can be routed by the bare `pre-commit` substring check in `_classify_text`, so remedy text mentioning `.pre-commit-config.yaml` may send the stall down the lint-failure recovery path instead of the ship-resume path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an early classifier branch for ship refresh stalls (for example `STALL_STEP=pr-create-guideline-outcome-refresh` and/or commit-failed refresh evidence) that returns `transient-infra` / `step8-shippr` before the lint token check, or reword the remedy to avoid the `pre-commit` substring; extend stall-recovery classify tests with remedy-bearing hook-failure evidence.


### FINDING_3: De-terminalize placement conflicts with recovery flow
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The plan places ship-state de-terminalization too early in `run_ship`, before later early-return recovery branches have finished, so the stalled overlay can be cleared before merged/done reconciliation reads it and the reship path can break.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Use one placement rule in the ship.py section: invoke the helper only after those early-return branches complete and immediately before the first pre-PR work that can call flush_logs_pre; assign ctx from the returned RunContext there. Remove the conflicting run_ship-entry-after-blocked-resume wording.

