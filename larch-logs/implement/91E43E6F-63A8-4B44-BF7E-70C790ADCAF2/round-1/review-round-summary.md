# Review Round 1

- Mode: `diff`
- 3 accepted, 6 rejected (4 neutral)

## Accepted Findings

### FINDING_1: Missing plan-mandatory pytest parity coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-waterfall-parity-output.txt, dyn-teardown-safety-output.txt
- **Severity**: important
- **Concern**: `python/test_agent_waterfall.py` is now the sole behavioral authority after deleting `scripts/test-dispatch-with-waterfall.sh`, but it omits many plan-mandatory and retired-harness parity cases. Regressions in per-phase launch-then-collect concurrency, SIGTERM subtree teardown, phase-3 tail `collect-results` replay (without `--summary-only`), WARN threshold / `cost-fallback-exceeded-threshold`, competition-notice forwarding, two-slot paths-file ordering, embedded-space paths, degraded-Cursor (`CURSOR_EMPTY_RESPONSE`), broader `--no-fallback` matrices, invalid first-line ERE preflight, and related aggregate-gate cases can ship while `make test-dispatch-with-waterfall` stays green. The existing phase-3 hard-fail test does not assert the separate tail collect-results replay.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the plan-listed pytest cases: per-phase single collect-results, SIGTERM subtree kill, WARN threshold, competition notice, two-slot order, embedded-space paths, and invalid first-line ERE preflight.
  - From cursor-specialist-correctness-output.txt: Spy on collector argv and require a second collect-results call without --summary-only for phase3_failed paths.
  - From codex-specialist-correctness-output.txt: Add the missing pytest cases from the plan.
  - From cursor-specialist-edge-cases-output.txt: Add the missing pytest cases from the plan, prioritizing SIGTERM teardown and multi-slot phase-1 concurrency plus tail-replay argv assertion.
  - From cursor-specialist-testing-output.txt: Port the retired harness matrix into python/test_agent_waterfall.py and sync docs/linting.md to asserted cases.
  - From codex-specialist-testing-output.txt: Port the missing retired-harness cases into python/test_agent_waterfall.py, including concurrency, tail replay, SIGTERM, full no-fallback, degraded Cursor, and aggregate invalid/no-match tests.
  - From dyn-waterfall-parity-output.txt: Port the remaining retired-harness cases and plan-pinned cases into python/test_agent_waterfall.py before relying on the deleted bash harness; at minimum add concurrency, SIGTERM, WARN threshold, tail-collector argv, and degraded-cursor tests called out in the plan acceptance block.
  - From dyn-teardown-safety-output.txt: Add a pytest that launches a stub launcher which forks a long-lived child, SIGTERMs the dispatcher mid-phase, and asserts the child process group is gone (e.g. poll `pgrep` or a sentinel file) and exit code is `143`.


### FINDING_11: SIGTERM teardown may miss detached descendants after launcher reaped
- **Reviewer(s)**: dyn-teardown-safety-output.txt
- **Severity**: important
- **Concern**: `_kill_active_launches` only calls `_terminate_launch` when `launch.process.poll() is None`. After `_reap_phase` waits out the launcher PID, external-agent descendants that detached into their own session are no longer in `_ACTIVE_LAUNCHES` and are not visited by `_descendants` on SIGTERM. A cancel after launcher exit but while a detached child still runs will exit 143 without killing that child.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-safety-output.txt: Track launcher PIDs (or a pgid set) for the whole dispatch until phase `collect-results` completes, and on SIGTERM/`atexit` always run `_descendants` + `killpg`/`SIGKILL` for every PID launched in the current dispatch, even if the top-level `Popen` has already reaped.


### FINDING_4: Paths-file write failures emit success KVs before crashing
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: When `--paths-file` points at an existing directory or unwritable destination, success KVs are emitted first; then `Path.replace` raises an uncaught `OSError` and exits 1, leaving misleading success output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Write and validate the paths file before success KVs and convert OSError to ValidationError exit 2.


