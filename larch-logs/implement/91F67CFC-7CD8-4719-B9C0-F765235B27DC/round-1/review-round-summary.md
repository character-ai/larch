# Review Round 1

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Step 0 cleanup runs before PID validation
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-session-cleanup
- **Severity**: minor
- **Concern**: `step0_abort_cleanup_main` still deletes `DESIGN_TMPDIR` before validating or safely handling `--claude-pid`, so malformed input can remove recovery state, raise an uncaught `ValueError`, and leave PID residuals behind. The invalid-PID edge case is also missing explicit test coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: `Validate ns.claude_pid before tmpdir cleanup, or map reap ValueError to a clean nonzero exit without deleting tmpdir first.`
  - From codex-specialist-edge-cases: `validate claude_pid before cleanup or catch ValueError at the call sites and return a normal diagnostic rc`
  - From cursor-specialist-testing: `Add reap_pid_residuals invalid-pid tests; validate --claude-pid before cleanup or catch ValueError and return a documented rc without reaping.`
  - From dyn-dyn-session-cleanup: `Validate ns.claude_pid (same _validate_claude_pid helper) before tmpdir cleanup; on failure print a stderr diagnostic and return CONFIGURATION_ERROR_RC (2) without calling cleanup-tmpdir. Wrap the reap call in a controlled error path if you still want post-cleanup failures to return a documented rc instead of a traceback.`


### FINDING_2: Step 6 cleanup runs before PID validation
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-session-cleanup
- **Severity**: minor
- **Concern**: `step6_cleanup_core` still deletes the design tmpdir before validating or handling `parsed.claude_pid`, so malformed input can erase the `.completed/step-6` state and then raise `ValueError`. The preserve-path tests also do not explicitly assert that reap stays skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: `Validate parsed.claude_pid before cleanup_tmpdir_main or fail at parse time like other session verbs.`
  - From cursor-specialist-testing: `Add fail_reap monkeypatches or residual-presence assertions on each Step 6 preserve early-return path.`
  - From dyn-dyn-session-cleanup: `Require and validate parsed.claude_pid before cleanup_tmpdir_main; only call reap_pid_residuals after both validation and successful tmpdir cleanup, returning a documented non-zero rc on validation or reap failure.`


### FINDING_7: Symlink containment checks are missing from reap cleanup
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: `reap_pid_residuals` still unlinks fixed paths without the ancestor/symlink guard used by the writers, so a symlinked cache root or parent could redirect cleanup outside the intended session tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: `validate each target with larch_io.assert_no_symlink_path_or_ancestors() or equivalent containment checks before unlinking, and fail closed on any symlinked ancestor`
