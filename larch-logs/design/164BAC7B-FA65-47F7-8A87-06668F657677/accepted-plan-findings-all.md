### FINDING_1: Regression test needs a live-like TMPDIR/IMPLEMENT_TMPDIR setup
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Workflow Artifact Regression
- **Severity**: important
- **Concern**: The proposed regression test may not faithfully reproduce the live failure or may assert an end-to-end success contract that the current fix scope cannot satisfy, because nested `run-log write` still depends on ambient `TMPDIR`, `tempfile.gettempdir()` may ignore a bad `TMPDIR`, and the test currently omits the live Step 5 `IMPLEMENT_TMPDIR` envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Tighten the test contract: add a positive check that write-tally-record.* lands under Path(--log-root).parent, and either stub only the nested proc.run run-log write leg or document that offline repro with a dead TMPDIR cannot require end-to-end rc==0 until run_log_batch._redact_to_temp is separately hardened (explicitly out of scope for this issue).
  - From Cursor-Innovation: Shape the test so unfixed code fails before the fix: call write_tally_main in-process with monkeypatched tempfile.gettempdir returning a nonexistent directory, or use a TMPDIR candidate that gettempdir() actually selects yet cannot host write-tally-record.* (verify red-green once). Keep asserting rc 0, tally JSON presence, and that the poisoned TMPDIR path was not created
  - From Cursor-Requirements: Revise the test contract: either (a) assert the record stages under Path(log-root).parent and that the bad TMPDIR tree was not created, without requiring full e2e success under impossible TMPDIR, or (b) use a live-like malformed TMPDIR (existing impl parent plus concatenated /var/folders/.../T suffix) and only require rc=0 plus JSON when that repro actually reaches run-log successfully; keep run-log hardening out of scope unless the narrowed test still fails.
  - From Cursor-dyn-Workflow Artifact Regression: Use a mkdir decoy TMPDIR (live-shaped malformed path that exists): monkeypatch TMPDIR to it assert no write-tally-record.* files appear under the decoy while code-review-tally.json lands under log-root; or keep nonexistent TMPDIR only to assert staging never touches it and drop the rc==0 assertion unless inner mkstemp is also hardened (explicitly out of scope here)
  - From Cursor-Innovation: In the new test set IMPLEMENT_TMPDIR to the same directory used as Path(log_root).parent (pytest tmp_path), keep malformed TMPDIR, then run write-tally through run_cli as planned


### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/report/test_run_logs.py:1506-1530
- **Concern**: Plan adds _rebase_under_tmpdir unit tests but omits updating the existing integration test that depends on pseudo-absolute input rebasing. Scenario: `test_larch_log_write_rebases_root_relative_log_root_and_input_file` passes `--input-file /token-report.json` while the payload lives at `session/token-report.json`; today `_rebase_under_tmpdir` maps that to `IMPLEMENT_TMPDIR/token-report.json`. The planned `return candidate` arm leaves `/token-report.json` as a real root path, so `run-log write` will ENOENT and the test will fail after the production fix
- **Proposed resolution**: Add `### UPDATED: python/tests/report/test_run_logs.py` step to revise that integration test: keep the `/larch-logs` log-root rebase assertion, but pass a real session path for `--input-file` (for example `str(source)`), or split input-file coverage into the new `_rebase_under_tmpdir` unit cases


