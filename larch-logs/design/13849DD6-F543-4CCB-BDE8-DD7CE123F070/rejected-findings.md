### [Plan Review] FINDING_2

### FINDING_2: Add Step 0 abort cleanup-failure no-reap regression test
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: minor
- **Concern**: The Step 0 abort cleanup-failure path lacks regression coverage for the no-reap gate, so reorder or reap-after-failure regressions could ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a test that forces cleanup-tmpdir failure (via the existing subprocess.run monkeypatch), asserts reap_pid_residuals is not invoked, and asserts the three PID cache files remain under Path.home()/.cache/larch/sessions/
  - From Cursor-Innovation: Add a step0_abort_cleanup_main test that mocks cleanup_tmpdir_main returning non-zero, asserts reap_pid_residuals is not called, and PID cache files remain


