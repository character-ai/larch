# Review Round 1

- Mode: `diff`
- 3 accepted, 4 rejected (0 neutral)

## Accepted Findings

### FINDING_1: scenario 5 can false-pass via the both-dead fast-unlink path
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-bgjob-process
- **Severity**: major
- **Concern**: `scripts/test-bgjob.sh` scenario 5 can pass without proving that `reap_main` took the expired-terminate branch while the decoy daemon was still live. If the decoy daemon dies first, reap can fast-unlink the registry row and the test still passes, so the no-signal terminate-path coverage is not actually proven.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-bgjob-process: Immediately before `python3 python/cli.py bgjob reap`, assert the decoy daemon is still alive (`kill -0 "$daemon_pid"`) and assert branch preconditions via a small Python probe that `registry.daemon_liveness(entry).live is True`, `registry.child_liveness(entry).live is False`, and `registry.entry_expired(entry) is True`, failing the test if any check fails so a both-dead shortcut cannot masquerade as terminate-path coverage.


### FINDING_3: daemon startup should reject invalid timing overrides up front
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Invalid owner-grace / poll-interval timing overrides are still being validated too late, after startup or only inside `_monitor`. That allows a daemon to report `STARTED` and then die without a typed failure result, instead of rejecting the bad override before startup succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-edge-cases: Write override parse failures to stderr log and/or a minimal result env with BGJOB_ERROR before cleanup.
  - From codex-specialist-edge-cases: Validate owner grace and poll interval before writing the startup pipe or return a clear BGJOB_ERROR before start succeeds.


### FINDING_4: bgjob harness should not capture long-lived launchers in command substitution
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The harness captures long-lived launchers through command substitution, so descendants inherit the capture pipe and the assignment blocks until the daemon or sleeper exits. That can delay owner-death setup and make `spawn_sleeper` appear hung until its child exits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Detach sleeper stdout and stderr, for example with subprocess.DEVNULL, before printing the PID.


