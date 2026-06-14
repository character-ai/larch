# Review Round 4

- Mode: `diff`
- 5 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: FileNotFoundError misclassified as probe timeout (EXIT 124)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: In `python/agents.py` (~709–710), `FileNotFoundError` is mapped to `EXIT_TIMEOUT` (124) like a real timeout. When the binary is on PATH but exec fails, the health gate reports timeout and fast-fails with misleading diagnostics instead of distinguishing launch failure from probe timeout. `*_PROBE_TIMED_OUT` should be set only on `TimeoutExpired`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Return separate codes for timeout vs launch failure; set `*_PROBE_TIMED_OUT` only on `TimeoutExpired`.


### FINDING_2: Missing presence key no longer fail-opens (Python + shell health gate)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: The new health gate treats missing `CURSOR_PRESENT=` / `CODEX_PRESENT=` as `"false"` and retries then fast-fails, instead of fail-opening on unparseable or absent keys. On main, empty or malformed probe stdout without a presence key immediately fail-opens. Regression spans `python/agents.py` (~1424–1437) and `scripts/lib-external-launcher-common.sh` (shell callers ~256–263 and external launch path ~5409–5428). If `agent check-reviewers` crashes or emits only an error banner without the selected presence key, external launches can be blocked or delayed incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Restore immediate fail-open when the presence key is absent; keep retries for explicit false and timed-out probes only.
  - From codex-generic-output.txt: Treat a missing selected presence key as unparseable output and fail open. Only retry or fast-fail on explicit `..._PRESENT=false` or `..._PROBE_TIMED_OUT=true`.


### FINDING_3: Health gate shells out to CLI instead of calling `check_reviewers()` in-process
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-caller-cutover-output.txt
- **Severity**: important
- **Concern**: `_external_health_gate()` in `python/agents.py` (~1360–1437) still invokes `python/cli.py agent check-reviewers` via `_invoke_health_gate_check_reviewers()` instead of calling `check_reviewers()` directly, contrary to the plan and the `session_env.py` cutover pattern. This adds a second Python process, stacks an outer `subprocess.run(..., timeout=…)` on inner probe timeout, and spends health-gate budget on CLI startup before probes run. Spurious `health-probe timed out` / `health-probe fast-fail` on slow hosts is more likely while pytest health-gate tests (mocking the subprocess helper, not `check_reviewers`) stay green; env, skip-flag, or timeout regressions on the direct API can pass CI while `run_external_agent` misclassifies tool health.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Replace `_invoke_health_gate_check_reviewers` with a direct `check_reviewers(skip_codex_probe=..., skip_cursor_probe=..., probe_timeout_seconds=timeout, env=gate_env)` call and mock `agents.check_reviewers` in health-gate tests.
  - From dyn-caller-cutover-output.txt: Replace the CLI subprocess in `_external_health_gate()` with a direct `check_reviewers(skip_…, probe_timeout_seconds=timeout, env=gate_env)` call, keep KV parsing only where a string envelope is still required, and add one integration test that exercises the real in-process path under a tight `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT`.


### FINDING_4: Negotiation-round tests omit `RESPONSE_FILE=` envelope assertions on exit 2
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test_run_negotiation_round_codex_auth_setup_failure_exit_2` and `test_run_negotiation_round_cursor_probe_failure_exit_2` in `python/test_agents.py` (~1152–1176) assert exit code 2 only, not the `RESPONSE_FILE=` stdout envelope required on exit 2/3. Removing `_emit_kv("RESPONSE_FILE", ...)` on auth-setup or Cursor command-failure paths would pass pytest and break negotiation wrappers that parse `RESPONSE_FILE=`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add capsys assertions for `RESPONSE_FILE=<output>` on both tests, matching the existing codex-failure and cursor-preflight tests.


### FINDING_7: Bash health-gate harness does not assert probe env knobs on retry
- **Reviewer(s)**: dyn-caller-cutover-output.txt
- **Severity**: important
- **Concern**: Six bash health-gate call sites in `scripts/lib-external-launcher-common.sh` (~168–221) depend on inline env prefixes (`LARCH_PROBE_TIMEOUT_SECONDS=…`, and `LARCH_PROBE_TTL_SECONDS=0` on retry) around `python3 … agent check-reviewers`, but `scripts/test-lib-external-launcher-common.sh` (~711–733) stubs record only argv (`ARGS=…`) and `LARCH_EXTERNAL_AUTH_RETRIES`, not those env knobs. A cutover regression that drops TTL bypass on retry or stops forwarding the outer timeout would still pass the bash harness while Python-only `_external_health_gate` tests stay green, restoring the stale-false-stamp failure mode retries are meant to prevent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-caller-cutover-output.txt: Extend the stub or checker-call log to capture `LARCH_PROBE_TIMEOUT_SECONDS` and `LARCH_PROBE_TTL_SECONDS` per invocation, and assert attempt 1 omits TTL bypass while attempts 2+ set `LARCH_PROBE_TTL_SECONDS=0` with the resolved timeout on every call.


