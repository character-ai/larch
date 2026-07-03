### OOS_1: [OUT_OF_SCOPE] Warning-triggered refresh failure hard-resets and can lose the warning
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-runlog-flush
- **Severity**: important
- **Concern**: On the normal CI-fix path, a warning-triggered refresh failure can return `pending=False`, so `_run_cycle` hard-resets to `baseline_head` and a later retry can skip flushing the warning that is still sitting in tmpdir. That leaves the warning only in tmpdir and can reopen the flush-timing bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Track pending warning flush state independent of callback return or re-flush when execution-issues.md changed since last sentinel
  - From cursor-specialist-correctness: Preserve pending warning state or avoid hard reset when refresh blocked for warning_logged
  - From cursor-specialist-edge-cases: Return a retry-preserving pending flag (or distinct status) on warning-triggered refresh failure and do not hard-reset; optionally key refresh off execution-issues.md vs .execution-issues-flushed.sha mismatch.
  - From cursor-specialist-testing: Preserve pending-warning state or flush based on unflushed execution-issues content, not only callback True
  - From dyn-dyn-runlog-flush: On warning-triggered refresh failure, return `pending=True` (or a distinct outcome) from `stage_and_push`, and teach `ci_agentic_fix` not to hard-reset on that path. Preserve the CI-fix commit and retry flush/push until refresh succeeds or the cycle exhausts.
  - From dyn-dyn-runlog-flush: Have the pre-push callback (or `_refresh_before_stage_push`) treat “unflushed execution issues present” as refresh-required, reusing the same predicate as `run_log_flush._should_flush_execution_issues` (step7a sentinel / flushed-sha / batch state), not only “this call appended a warning.”

### OOS_2: [OUT_OF_SCOPE] Normal CI-fix push path still lacks an ndjson integration test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The only real flush+ndjson coverage is on the pending-rebase force-push seam. The normal commit-and-push path is still covered by a mocked ordering test, so a regression there could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add stage_and_push test with delta_paths, real flush, callback True, assert ndjson before git push

### OOS_3: [OUT_OF_SCOPE] Resume PR-create path still lacks a real-flush regression test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The open-PR resume path skips the postbump flush, so only the pin-triggered seam protects late warnings, but the current resume test does not prove that seam writes `execution-issues.ndjson`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add resume run_ship test with pin_warning_logged=True and ndjson assertion before ensure_pr
