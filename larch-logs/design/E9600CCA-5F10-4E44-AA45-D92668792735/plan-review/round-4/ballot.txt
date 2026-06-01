### FINDING_1: Fix-attempt flag may reset across outer attempts
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `_code_fix_attempted_on_ready_log` must be initialized once outside the retry/fix-loop. If it is initialized inside the loop body with other per-iteration state, a substantive fix attempt from an earlier attempt can be cleared before exhaustion, causing terminal classification to report `exit_stall` instead of autonomous `ci-fix-exhausted`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Declare/init the flag once with the other `run_evaluate_failure` locals immediately before the `while`; never reassign false inside the loop; only set true per the predicate

### FINDING_2: Blind-rerun log capture can be overwritten by rerun stderr
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The upfront `gh-run-logs` capture for blind rerun can use the same failure-capture path later redirected as `ci-rerun-failed.sh` stderr. Because `2>` truncates the path, the fix loop may stash or pass rerun stderr as though it were CI logs, especially after a transient rerun attempt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Use two paths: `upfront_logs=$(failure_capture_path "$phase")` for `gh-run-logs`, separate `rerun_fail=$(failure_capture_path "$phase")` for rerun stderr; stash `upfront_logs` only when blind rerun is skipped (deterministic/non-ready) or not attempted—never after rerun writes the shared file
