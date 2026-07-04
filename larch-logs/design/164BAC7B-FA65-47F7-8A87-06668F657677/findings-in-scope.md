### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/report/test_run_logs.py:1506-1530
- **Concern**: Plan adds _rebase_under_tmpdir unit tests but omits updating the existing integration test that depends on pseudo-absolute input rebasing. Scenario: `test_larch_log_write_rebases_root_relative_log_root_and_input_file` passes `--input-file /token-report.json` while the payload lives at `session/token-report.json`; today `_rebase_under_tmpdir` maps that to `IMPLEMENT_TMPDIR/token-report.json`. The planned `return candidate` arm leaves `/token-report.json` as a real root path, so `run-log write` will ENOENT and the test will fail after the production fix
- **Proposed resolution**: Add `### UPDATED: python/tests/report/test_run_logs.py` step to revise that integration test: keep the `/larch-logs` log-root rebase assertion, but pass a real session path for `--input-file` (for example `str(source)`), or split input-file coverage into the new `_rebase_under_tmpdir` unit cases



