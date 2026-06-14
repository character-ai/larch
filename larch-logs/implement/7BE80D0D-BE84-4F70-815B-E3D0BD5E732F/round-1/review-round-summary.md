# Review Round 1

- Mode: `diff`
- 5 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Health gate does not fast-fail on probe subprocess timeout
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-probe-parity-output.txt, dyn-caller-cutover-output.txt
- **Severity**: important
- **Concern**: After porting health checks to in-process `check_reviewers()`, `_external_health_gate()` no longer treats probe subprocess timeouts as immediate unhealthy outcomes. `_run_probe_command()` swallows `subprocess.TimeoutExpired` and returns `config.EXIT_TIMEOUT` (124), which becomes `CODEX_PRESENT=false` / `CURSOR_PRESENT=false` in KV output. The gate treats that as a failed presence probe and retries up to `LARCH_EXTERNAL_HEALTH_GATE_MAX_ATTEMPTS` (default 8) with inter-attempt sleeps, so a single hung Codex/Cursor probe can block `run_external_agent` for minutes instead of failing once within `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT`. The `except TimeoutError` branch at `python/agents.py:1309-1310` is effectively dead because nothing raises `TimeoutError` on this path. Bash callers still get immediate fast-fail via wrapper exit 124/143.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-parity-output.txt: **Suggested fix:** Treat inner timeout (`rc == config.EXIT_TIMEOUT` or equivalent) like the old exit 124/143 path: return unhealthy immediately with the same diagnostic string, without consuming the multi-attempt retry loop.
  - From dyn-caller-cutover-output.txt: **Suggested fix:** Treat probe return code `124`/`config.EXIT_TIMEOUT` (and optionally hung wall-clock over the resolved health-gate timeout) as an immediate `(False, "health-probe timed out after …")` return inside `_external_health_gate()`, matching the bash `case "$probe_rc" in 124|143)` behavior; add a pytest that stubs `_run_one_*_probe` to return `EXIT_TIMEOUT` and asserts no multi-attempt retry loop.


### FINDING_2: Health gate timeout does not bound full `check_reviewers()` wall clock
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-probe-parity-output.txt
- **Severity**: important
- **Concern**: `_external_health_gate()` passes `probe_timeout_seconds=timeout` only to the inner Codex/Cursor child probe via `_run_probe_command()`. Unlike the retired subprocess wrapper that bounded the entire `check-reviewers.sh` process, preflight work, stamp I/O, and `external_serial_lock_acquire()` (up to `LARCH_EXTERNAL_SERIAL_LOCK_TRIES` × 0.1s, default ~30s on Darwin) can run before the child timeout starts. With `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=1` and a held serial lock, launch fast-fail can be delayed well past the configured health timeout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-parity-output.txt: **Suggested fix:** Restore a per-attempt wall-clock budget around the whole `check_reviewers()` call (for example `subprocess.run` on the CLI, or a deadline passed through the probe helpers), matching the old subprocess wrapper semantics; keep `probe_timeout_seconds` as an inner bound only if needed.


### FINDING_6: Cursor preflight rc=2 setup chain does not match retired Bash contract
- **Reviewer(s)**: dyn-probe-parity-output.txt
- **Severity**: important
- **Concern**: In retired `scripts/check-reviewers.sh`, when `cursor_auth_preflight` returned 2, a failed `larch_cursor_probe_setup_chain` set `CURSOR_PRESENT=false` without running a live probe. The Python port always calls `_probe_with_retries("cursor", 1, ...)`, which enters `_run_one_cursor_probe()`; setup failures such as `mkdtemp` / `NamedTemporaryFile` errors raise `OSError` instead of yielding `cursor_present=False`. That can crash `check_reviewers_main` for CLI callers, and in `_external_health_gate()` the broad `except Exception` at `python/agents.py:1311-1313` fail-opens (marks the tool healthy) on setup exceptions rather than recording a clean failed probe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-parity-output.txt: **Suggested fix:** Hoist the Cursor setup chain (preread, export, private config dir) ahead of the live probe, mirror the Bash `setup chain failed → present=false` branch for both preflight modes, and only run `_run_one_cursor_probe()` when setup succeeds.


### FINDING_8: Plan-mandated pytest cases not ported from retired Bash harnesses
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Required pytest coverage from retired bash harnesses was not fully ported: invalid env normalization, non-auth no-retry, auth-setup failures, cursor negotiation exit 2, probe temp-home/secret scans, and related argv regressions. These gaps can ship while `make test-check-reviewers` and `make test-run-negotiation-round` stay green.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_9: Makefile `test-check-reviewers` filter excludes health-gate tests from lint shard
- **Reviewer(s)**: dyn-caller-cutover-output.txt
- **Severity**: important
- **Concern**: `make test-check-reviewers` was retargeted to `python3 -m pytest python/test_agents.py -q -k check_reviewers`, but the plan requires `-k 'check_reviewers or negotiation_round or health_gate'`. Tests such as `test_health_gate_timeout_resolves_session_env`, `test_health_gate_fail_open_on_unparseable_probe`, and `test_run_external_agent_health_gate_fast_fails_without_spawn` in `python/test_agents.py:1031-1144` are excluded from the `make lint` prerequisite shard (`test-harnesses-4`), so health-gate integration regressions on the Python `run-external-agent` path can ship while the Make target stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-caller-cutover-output.txt: **Suggested fix:** Align the Makefile filter with the plan (`-k 'check_reviewers or health_gate'`), or split a dedicated `test-health-gate` target and add it to the harness shard.


