### FINDING_1: Step 0 ordering tests need full sequence coverage
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-Step0 Progress Order, Codex-dyn-Step0 Progress Order
- **Severity**: major
- **Concern**: The Step 0 test coverage only checks one activate-vs-timing ordering point, so it can still pass if the old pre-setup `timing mark` remains, if the visible session-setup mark appears before `progress activate`, or if `progress activate` is moved ahead of `write-design-env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In the new Step 0 session tests, capture all subprocess/`_run_best_effort` commands and assert there is exactly one `timing mark` for `design Step 0: session setup`, that it runs only after `progress activate`, and that no such timing command runs before `session setup` completes
  - From Cursor-dyn-Step0 Progress Order: Record ordered `subprocess.run` argv in Step 0 tests; assert no `timing`/`mark` for `design Step 0: session setup` occurs before `session setup`, then assert `progress activate` precedes the sole remaining session-setup timing mark; discriminate `token mark` with `cmd[2:4] == ["token", "mark"]`
  - From Codex-dyn-Step0 Progress Order: Extend the new command-capture test to record all subprocess calls and assert the full sequence: session setup -> write-design-env -> progress activate -> timing mark.

### FINDING_2: Nested repo-root parity for activation
- **Reviewer(s)**: Cursor-dyn-Step0 Progress Order
- **Severity**: minor
- **Concern**: The nested-working-directory parity check covers `write-design-env`, but it does not pin that `progress activate` uses the same resolved repo root in nested clones.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Step0 Progress Order: Extend `test_step0_session_threads_repo_root_to_design_env` to also capture `progress activate` and assert its `--repo-root` equals the git toplevel already asserted for `write-design-env`, instead of adding a second nested fixture ## Review summary
