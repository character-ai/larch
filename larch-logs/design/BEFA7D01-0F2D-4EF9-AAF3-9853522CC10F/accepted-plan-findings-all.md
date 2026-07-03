### FINDING_1: Flush-failure logging must stay best-effort
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The flush-failure path still lets `run_logs.append_execution_issue(...)` raise, so a warning write can turn a normal `complete` or `cap-hit` exit into a Step 5 stall/internal-error instead of preserving the successful result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Wrap append_execution_issue in contextlib.suppress(OSError), matching _append_record_escalation_tool_failure (line 437-438); keep _err(stderr) warning unconditional
  - From Codex-Arch: Keep the stderr warning, but wrap the execution-issue append in its own best-effort suppression so logging failure cannot change Step 5's terminal rc or envelope.
  - From Cursor-Innovation: In _flush_review_batches_for_result, use try/except that logs via _err, appends a Warnings execution issue, and returns normally; never re-raise. Add an explicit plan note that the wrapper must not propagate exceptions to the outer handler, or the fix reintroduces a stall on the two success paths
  - From Codex-Innovation: Wrap the warning append in its own best-effort `try/except` or `contextlib.suppress(...)`, and keep `_err(...)` as the only mandatory side effect in the flush-failure path
  - From Codex-Pragmatic: Wrap the warning append in best-effort suppression so the exception path cannot change the Step 5 return code.
  - From Codex-Requirements: Wrap the execution-issues append in its own `try/except` or `contextlib.suppress(OSError)` so a failed warning write cannot turn the flush failure into a hard Step 5 error.


### FINDING_4:
- **Reviewer(s)**: Codex-dyn-Step5 Runlog Contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_and_fix.py:524-534,740-744
- **Concern**: [SCOPE-REDUCTION] Drop the `execution-issues.md` append from the flush-failure path, or make it best-effort only.. Scenario: `run_logs.append_execution_issue(...)` at `python/larch/report/run_log_batch.py:419-420` writes directly to disk, so a transient I/O failure on a normal `complete` or `cap-hit` exit can still fall into the outer `except` at `review_and_fix.py:740-744` and return 2 even though the review succeeded.
- **Proposed resolution**: Keep only the stderr warning, or guard the append so its own failure cannot change the Step 5 rc.


