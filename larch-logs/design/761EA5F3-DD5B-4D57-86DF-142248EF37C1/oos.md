### FINDING_2: Preserve the Cursor external execution envelope and injected-runner seam
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: A descriptor migration could execute the Cursor leaf command directly or use in-process subprocess helpers, losing the injected runner seam, timeout and stall handling, prompt wrapping, startup locking, capture, and failure diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: State in the plan that the Cursor execute hook must still invoke `run-external-agent` (or byte-equivalent helper) around the `lint-fix-write` leaf argv, and keep an integration test asserting that wrapper remains in injected-runner calls.
  - From Cursor-Pragmatic: Name the outer execute stack explicitly in checks_lint_fix.py and add parity tests for run-external-agent envelope, cursor-wrap-prompt follow-up, startup lock, and wrapper-log capture alongside lint-fix-write exact-argv assertions. Keep inner lint-fix-write exact-argv tests, but do not retire test_run_lint_fix_cursor_argv_and_wrap_cwd without equivalent coverage.
  - From Cursor-Pragmatic: Add explicit plan steps and tests for the `run-external-agent` envelope, `cursor-wrap-prompt` follow-up, startup lock, and wrapper-log capture. Keep inner `lint-fix-write` exact-argv tests, but do not retire `test_run_lint_fix_cursor_argv_and_wrap_cwd` without equivalent coverage.
  - From Cursor-Requirements: Require lane execute hooks to invoke runner.run (or an equivalent runner-visible wrapper such as run-external-agent) and map CommandResult to VendorProcessResult; forbid in-process subprocess helpers in this lane


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] Factor shared Codex lint-fix launch hooks out of `launch_codex_exec_main` for lane import.
- **Description**: [OUT_OF_SCOPE] Factor shared Codex lint-fix launch hooks out of `launch_codex_exec_main` for lane import.. Scenario: The plan allows lane-local adapters duplicating `launch-codex-exec` hook wiring; that works but repeats logic already proven in `_drafter.launch_codex_exec_main`.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/agents/_drafter.py:464-537
- **Phase**: design

Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

