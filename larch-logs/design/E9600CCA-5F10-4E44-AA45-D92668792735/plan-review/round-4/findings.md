### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2520-2524; plan.txt:47
- **Concern**: `_code_fix_attempted_on_ready_log` init is anchored inside the fix-loop body (~2532+) alongside per-iteration defer rules. Scenario: Implementer may reset the flag each outer attempt (same place as `state_set_many BAIL_REASON ""`). A substantive attempt on attempt 1 is cleared before terminal exhaustion → `exit_stall` (4) instead of autonomous `ci-fix-exhausted` (3)
- **Proposed resolution**: Declare/init the flag once with the other `run_evaluate_failure` locals immediately before the `while`; never reassign false inside the loop; only set true per the predicate

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2499-2514
- **Concern**: Blind-rerun upfront `gh-run-logs` capture can share/truncate the same path as `ci-rerun-failed.sh` stderr. Scenario: Plan adds classification fetch then `ci-rerun-failed.sh ... 2>"$fail_file"` (today’s pattern). Redirect `2>` truncates the file. If iteration-1 reuse stashes that path after a transient rerun attempt, the fix loop can feed rerun stderr to `run_ci_fix_vendor` instead of CI logs
- **Proposed resolution**: Use two paths: `upfront_logs=$(failure_capture_path "$phase")` for `gh-run-logs`, separate `rerun_fail=$(failure_capture_path "$phase")` for rerun stderr; stash `upfront_logs` only when blind rerun is skipped (deterministic/non-ready) or not attempted—never after rerun writes the shared file
