## Proposed Design Outline

### Goals
- Fix the false "external tool unhealthy" banner in `step0_abort_cleanup_main` to print the caller-supplied reason and log the caller-supplied tool name.
- Reap all three PID-keyed session files after abort cleanup: `current-design-env-$PPID.sh`, `design-run-$PPID.sh`, and `step0-parsed-$PPID.env`.
- Extend Step 6 happy-path cleanup to also reap those three PID files.

### Non-goals
- Change `cleanup_tmpdir_main` itself (keep it dir-only).
- Add a dedicated postpone/cancel verb (parameterization covers the use case).
- Alter Step 6 eligibility or preservation logic.
- Touch `/larch:cleanup` (it already reaps dangling symlinks independently).

### Approach sketch
- Add `--reason` and `--tool` value flags to `_parse_wrapper_args` (new fields on `Step0WrapperNs`).
- Update `step0_abort_cleanup_main` to use those values in the banner and failure-log call, defaulting to today's degraded-tools strings.
- Add `reap_pid_residuals(claude_pid: str) -> None` to `session_env.py`; it silently unlinks all three PID-keyed paths using inline path helpers.
- Call `reap_pid_residuals` in `step0_abort_cleanup_main` after the tmpdir subprocess returns.
- Call `reap_pid_residuals` in `step6_cleanup_core` after `cleanup_tmpdir_main` returns 0.
- Update the existing test and add a reason-parameterization test.

### Surfaces in scope
- `python/larch/design/design_step0_env.py` (new `Step0WrapperNs` fields, `_parse_wrapper_args` flags)
- `python/larch/design/design_step0.py` (`step0_abort_cleanup_main`)
- `python/larch/state/session_env.py` (new `reap_pid_residuals` function)
- `python/larch/design/design_step6.py` (`step6_cleanup_core`)
- `python/tests/design/test_design_lifecycle.py` (update + add tests)

### Open questions
- None.
