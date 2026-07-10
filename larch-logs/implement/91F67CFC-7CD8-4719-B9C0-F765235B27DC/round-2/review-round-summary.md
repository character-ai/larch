# Review Round 2

- Mode: `diff`
- 1 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Leaf symlink cleanup blocks PID residual reaping
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing, dyn-dyn-session-cleanup
- **Severity**: major
- **Concern**: `reap_pid_residuals` applies the symlink/ancestor guard to `current-design-env-{pid}.sh`, but that path is intentionally the leaf symlink created during design-env setup. Cleanup therefore fails before unlinking the PID residuals, leaving the design-run and parsed-env files behind.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-session-cleanup: Reuse the writer contract for the env pointer only — e.g. call `_validate_design_current_env_link(symlink_path=target, pid=claude_pid)` (or an ancestor-only helper) for `_design_symlink_path`, then `target.unlink()` without resolving — and keep full `assert_no_symlink_path_or_ancestors` for the regular-file targets (`design-run-{pid}.sh`, `step0-parsed-{pid}.env`). Add a regression test that creates a real `current-design-env-{pid}.sh` symlink (dangling or not) and asserts all three residuals are removed.


