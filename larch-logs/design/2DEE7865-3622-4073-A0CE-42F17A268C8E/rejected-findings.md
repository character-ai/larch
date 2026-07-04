### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/report/test_run_logs.py
- **Concern**: `tempfile.tempdir` monkeypatch will not reliably steer `mkstemp` in pytest. Scenario: The plan patches `run_log_flush.tempfile.tempdir`, but `tempfile.mkstemp` uses cached `gettempdir()`; pytest/tmp_path usually calls that before the test body. Render output can stay in the real host `$TMPDIR` while the mock asserts it is under `system-tmp`, so correct code can fail. If the patch is a no-op, the test may still pass without proving the intended isolation.
- **Proposed resolution**: Patch `run_log_flush.tempfile.gettempdir` to return `str(system_tmp)`, or drop the fake `system-tmp` harness and assert only that `--output` is outside `implement-tmp` while `IMPLEMENT_TMPDIR` is set.




### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/report/run_log_batch.py:110-115
- **Concern**: [SCOPE-REDUCTION] Broad absolute-path passthrough removes the existing root-relative argv recovery contract. Scenario: Post-Step-0 fences can still invoke the stable launcher with caller-shell-expanded paths such as /execution-issue-record.ndjson. The old rebase mapped that to $IMPLEMENT_TMPDIR/execution-issue-record.ndjson, but the current passthrough reads /execution-issue-record.ndjson and the run-log append fails.
- **Proposed resolution**: Narrow the no-op to the external temp-file case needed by transcript capture and write-tally. Keep rebasing root-relative session paths whose target exists under IMPLEMENT_TMPDIR, and restore coverage for root-relative run-log write or append inputs.

