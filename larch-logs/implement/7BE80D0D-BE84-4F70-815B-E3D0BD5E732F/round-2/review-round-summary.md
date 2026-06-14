# Review Round 2

- Mode: `diff`
- 7 accepted, 3 rejected (3 neutral)

## Accepted Findings

### FINDING_1: _external_health_gate fail-open and unsafe fork in threaded parent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-caller-cutover-output.txt
- **Severity**: important
- **Concern**: `_external_health_gate()` uses multiprocessing with an explicit `fork` context on Darwin while the parent may already have active threads (for example from `external_serial_lock_release_after`). Fork-after-threads is a known hazard. When the child crashes, OOMs, wedges, or exits without sending on the pipe, or when `poll()` is false or an exception path is taken, the gate returns `(True, "")` and fail-opens, so `run_external_agent` may spawn an external tool despite a failed or inconclusive health check. The pre-migration path used a subprocess that did not fork the calling interpreter.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Treat empty pipe after child exit as unhealthy or retry; limit fail-open to unparseable presence output only.
  - From cursor-specialist-edge-cases-output.txt: Use spawn or a CLI subprocess for the gate probe; fail-closed when no parseable CODEX_PRESENT/CURSOR_PRESENT line is received.
  - From dyn-caller-cutover-output.txt: Prefer `subprocess.run` with a dedicated `python3 -m` / CLI invocation (same isolation as the bash retarget), or force `spawn` context for the health-gate child so the parent interpreter is never forked mid-run.


### FINDING_10: _cursor_probe_setup_chain fails on unreadable cli-config.json copy
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_cursor_probe_setup_chain()` returns `None` when copying `~/.cursor/cli-config.json` raises `OSError`. The retired Bash setup ignored that copy failure and still ran the Cursor probe, so a stale or unreadable config file can now make `CURSOR_PRESENT=false` even when `CURSOR_API_KEY` or keychain auth works.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Treat the config copy as best-effort. Only fail setup when the private temp config dir cannot be created.


### FINDING_11: _prepare_codex_home uncaught OSError can break KV contract
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Codex probe setup calls `_prepare_codex_home()` without catching filesystem errors from reading `~/.codex/config.toml`. If that file exists but is unreadable, `agent check-reviewers` can raise instead of emitting the required KV contract, and `agent run-negotiation-round` can miss the required `RESPONSE_FILE=` exit-2 envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Catch `OSError` in `_prepare_codex_home()` and return a nonzero `(rc, message)`, or catch it at both new call sites and map it to probe-false / negotiation exit 2.


### FINDING_2: Shell vs Python probe_timed_out handling diverges
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-probe-parity-output.txt
- **Severity**: important
- **Concern**: Internal probe timeout is a hard failure in Python `_external_health_gate` (fast-fail on `probe_timed_out`), but shell `external_launch_health_gate` cannot distinguish an internal probe timeout from other probe failures because `check_reviewers_main()` always exits 0 and does not surface `codex_probe_timed_out` / `cursor_probe_timed_out` in stdout. Shell paths therefore retry on `CODEX_PRESENT=false` / `CURSOR_PRESENT=false` until the outer `timeout` returns `124`/`143`, while `run_external_agent` fast-fails on the first `probe_timed_out`. Slow probes get different semantics across launcher surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Unify timeout handling across shell and Python gates (shared KV or exit code), or retry probe_timed_out like PRESENT=false.
  - From dyn-probe-parity-output.txt: Emit explicit timeout KVs from `check_reviewers_main()` (for example `CODEX_PROBE_TIMED_OUT=true` / `CURSOR_PROBE_TIMED_OUT=true`) or use a non-zero CLI exit for probe timeout, and teach `external_launch_health_gate` to treat that like the existing `124`/`143` fast-fail path instead of sleeping through the full retry budget.


### FINDING_7: Missing pytest for _external_health_gate retry and cache bypass
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required pytest coverage for `_external_health_gate` retries and cache bypass is missing. When `run_external_agent` health gating gets a transient false probe, a broken retry or missing `LARCH_PROBE_TTL_SECONDS=0` on later attempts could block launches without failing `make test-check-reviewers -k health_gate`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a pytest that forces one false then one true probe result and asserts recovery plus TTL=0 on the retry env.


### FINDING_8: Missing pytest for private Cursor config cleanup
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-listed private Cursor config cleanup test is not implemented. A regression that leaks `larch-cursor-cfg-*` dirs or leaves `CURSOR_CONFIG_DIR` set would not fail CI despite being an explicit plan acceptance item.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend or add a test that runs a cursor probe with mocked auth/setup and asserts temp config dirs and env restoration.


### FINDING_9: Shell health gate does not set LARCH_PROBE_TIMEOUT_SECONDS
- **Reviewer(s)**: dyn-probe-parity-output.txt, dyn-caller-cutover-output.txt
- **Severity**: important
- **Concern**: The retargeted bash health gate wraps `python3 … agent check-reviewers` with only the outer `timeout`/`gtimeout` envelope and does not set `LARCH_PROBE_TIMEOUT_SECONDS` to the resolved `timeout_seconds`, while `_external_health_gate()` passes `probe_timeout_seconds=timeout` into `check_reviewers()`. When `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` (or session-env) is above the default 30s probe cap, shell-launched paths cap each live probe at 30s, may return `CODEX_PRESENT=false` / `CURSOR_PRESENT=false`, and enter the 8×15s retry loop, but `run_external_agent`'s Python gate allows the full configured timeout per attempt and fast-fails on `probe_timed_out`. Launcher surfaces split behavior after the port.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-parity-output.txt: In every health-gate `agent check-reviewers` invocation, export `LARCH_PROBE_TIMEOUT_SECONDS="$timeout_seconds"` (alongside the existing `LARCH_EXTERNAL_AUTH_RETRIES=1` / retry `LARCH_PROBE_TTL_SECONDS=0` wiring) so shell and Python gates share one per-attempt probe budget.
  - From dyn-caller-cutover-output.txt: Export `LARCH_PROBE_TIMEOUT_SECONDS="$timeout_seconds"` on every health-gate probe invocation in `external_launch_health_gate`, and either parse a probe-timeout signal from CLI output or fast-fail when inner timeout equals outer bound, so bash and Python gates share the same timeout and retry semantics.


