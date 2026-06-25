# Review Round 2

- Mode: `diff`
- 2 accepted, 3 rejected (2 neutral)

## Accepted Findings

### FINDING_3: `_kill_leg_process_group()` gates SIGKILL on parent `wait()` timeout
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-generalist
- **Severity**: important
- **Concern**: `_kill_leg_process_group()` sends `SIGKILL` only when the top-level leg process is still alive after the TERM grace period. If the wrapper exits promptly on `SIGTERM` but same-process-group helpers or detached descendants ignore TERM, the function skips the KILL branch and returns timeout routing while survivors keep mutating the worktree or `$IMPLEMENT_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: After TERM/wait always re-probe live descendants and SIGKILL survivors regardless of parent wait outcome
  - From codex-generalist: Store the child pgid before sending TERM, then after the grace period always attempt `SIGKILL` against the pgid and the descendant snapshot/new descendants that are still alive, rather than gating escalation solely on `process.wait()` timing out.


### FINDING_11: Bash outer-fence `_larch_cleanup_active_leg` lacks pgrep-backed descendant teardown
- **Reviewer(s)**: dyn-dyn-timeout-process-groups
- **Severity**: important
- **Concern**: `_larch_cleanup_active_leg` in `bootstrap.py` only sends TERM/KILL to the published leg pgid from `.active-leg-pgid`. It does not mirror inner `_kill_leg_process_group()`'s `pgrep -P` descendant walk. Nested `start_new_session=True` reviewers live in separate sessions and are only reachable via per-PID kills. When Bash `EXIT`/`TERM` cleanup runs without the Python `_leg_signal_handler` path (wrapper crash/OOM, or parent hard-killed before the handler runs), those descendants can keep spending tokens and writing under `$IMPLEMENT_TMPDIR`/the worktree after the fence has returned routing tokens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-timeout-process-groups: Have the launcher trap delegate to the same teardown logic as `_kill_leg_process_group()` (for example a small `python/cli.py implement kill-active-leg --implement-tmpdir …` that reads `.active-leg-pgid` and runs the pgrep-backed group kill), or publish and signal descendant PIDs alongside the pgid so Bash cleanup matches the inner contract.


