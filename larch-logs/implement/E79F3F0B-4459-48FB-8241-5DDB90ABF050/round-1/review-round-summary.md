# Review Round 1

- Mode: `diff`
- 4 accepted, 7 rejected (3 neutral)

## Accepted Findings

### FINDING_1: Structure harness killpg needle mismatch (`process.pid` vs `pid`)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-implement-structure.sh` `require()` expects `os.killpg(os.getpgid(process.pid), signal.SIGKILL)` but `python/implement_dispatch.py` uses `os.killpg(os.getpgid(pid), signal.SIGKILL)` after `pid = process.pid`. The structure harness fails with a missing-needle error and blocks plan acceptance (`make test-harnesses-12` / static harness pass) despite working group-kill logic in the implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Update the require() needle to os.killpg(os.getpgid(pid), signal.SIGKILL) or equivalent substring that exists in the implementation file.
  - From cursor-specialist-edge-cases-output.txt: Update the harness needle to os.killpg(os.getpgid(pid), signal.SIGKILL) or change the killpg calls back to process.pid so the assertion matches.
  - From cursor-specialist-testing-output.txt: Align harness needle and implementation (use process.pid in code or relax require() to match the pid local).


### FINDING_10: Detached descendants survive leg-timeout cleanup (snapshot / kill order)
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-generalist-output.txt, dyn-dyn-composite-routing-output.txt
- **Severity**: important
- **Concern**: Timeout cleanup races detached descendants. `_kill_leg_process_group()` signals the leg process group before reliably capturing or terminating detached `start_new_session=True` children (e.g. reviewers from `python/agent_waterfall.py:457-459`). The leg child can exit or reparent descendants before `_descendants()` runs, so detached reviewers can keep spending tokens and writing under `$IMPLEMENT_TMPDIR` after the composite has already returned timeout routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Snapshot the child tree before signalling and kill that fixed set, or use a stronger subtree-reaping strategy that does not depend on parent-PID enumeration after the group kill.
  - From codex-generalist-output.txt: Snapshot the descendant tree before the first group signal, terminate those PIDs or process groups too, then rescan before final `SIGKILL` with bounded waits.
  - From dyn-dyn-composite-routing-output.txt: Snapshot `descendant_pids = _descendants(process.pid)` (and optionally the leg pgid) **before** any `killpg`/`kill`, then signal/kill that frozen PID set; only then `killpg` the leg group and `wait()`. Add an integration-style test where a mocked leg spawns a detached grandchild and assert it is gone after leg timeout.


### FINDING_11: Outer `larch-run.sh` timeout can kill wrapper before leg cleanup runs
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Per-leg cleanup runs only inside the Python wrapper. If the outer `larch-run.sh` timeout or a `SIGKILL` terminates the wrapper before signal or atexit hooks fire, the child leg (already in a separate session) can keep running and mutating `IMPLEMENT_TMPDIR` or the worktree after the composite has timed out, despite SKILL outer-timeout fences for `checks-commit-route` and `checks-step5-resume`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: make the outer fence participate in cleanup as well, or move timeout ownership to a wrapper that can always send TERM/KILL to the active leg session before the parent exits.


### FINDING_12: `Popen` context manager can unboundedly wait after timeout cleanup
- **Reviewer(s)**: codex-generalist-output.txt
- **Severity**: important
- **Concern**: `_run_leg_with_timeout` returns from inside a `with subprocess.Popen(...)` block after timeout cleanup. If `_kill_leg_process_group` suppresses a second `process.wait(timeout=2)` timeout, `Popen.__exit__` still performs an unbounded wait, so a stuck child can hang the composite parent past the hard deadline instead of emitting timeout routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist-output.txt: Avoid the `Popen` context manager here, close pipes explicitly, and ensure every post-timeout wait or drain is bounded before returning the `TimeoutExpired` result.


