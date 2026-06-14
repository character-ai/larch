# Review Round 5

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Partial `gate_env` replaces full process environment in health gate
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-generic-output.txt, dyn-probe-parity-output.txt, dyn-caller-cutover-output.txt
- **Severity**: important
- **Concern**: `_external_health_gate` passes only a partial `gate_env` (`LARCH_EXTERNAL_AUTH_RETRIES`, `LARCH_PROBE_TIMEOUT_SECONDS`, optional `LARCH_PROBE_TTL_SECONDS`) into `check_reviewers(env=...)`, but `check_reviewers` applies that through `_temporary_environ`, which replaces the entire `os.environ` instead of overlaying overrides. That strips `PATH`, `HOME`, `USER`, `TMPDIR`, and auth-related variables, so `shutil.which` can miss installed `codex`/`cursor` binaries and live probes can fail authentication. Healthy machines can see `CODEX_PRESENT=false` / `CURSOR_PRESENT=false` and fast-fail `run_external_agent` with exit 7/8 before the real agent spawns, unlike the retired Bash/subprocess path that merged overrides onto `dict(os.environ)`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Merge gate_env onto os.environ before calling check_reviewers (env={**os.environ, **gate_env}) or make _temporary_environ overlay-only for health-gate callers.
  - From cursor-specialist-edge-cases-output.txt: Merge gate_env onto a copy of os.environ instead of clearing the environment; or stop using env= for partial overrides.
  - From cursor-specialist-testing-output.txt: Merge gate_env over os.environ (or use overlay semantics) and add an unmocked integration test with a fake codex on PATH
  - From codex-generic-output.txt: Pass a merged environment, such as `{**os.environ, **gate_env}`, or make `_temporary_environ` treat its argument as overrides. Add a regression that health-gate probes preserve `PATH` and auth env.
  - From dyn-probe-parity-output.txt: Merge before the temporary override, e.g. `check_reviewers(..., env={**os.environ, **gate_env})`, or change `_temporary_environ()` to overlay keys instead of replacing the whole environment when `env` is meant as overrides only; add an integration test that calls `_external_health_gate()` without mocking `check_reviewers()` and asserts binaries/auth env are visible during the probe.
  - From dyn-probe-parity-output.txt: Split contracts: either rename/document `env=` as “full probe environment” and require callers to pass a complete dict, or add a separate overlay path (e.g. `env_overrides=`) used by the health gate while tests keep full replacement via an explicit test-only parameter.
  - From dyn-caller-cutover-output.txt: Merge, do not replace: pass `{**os.environ, **gate_env}` from `_external_health_gate()`, or change `_temporary_environ()` to overlay keys onto a copy of the current environ. Add a non-mocked test that stubs only `PATH`/binaries and proves `_external_health_gate("codex")` can return healthy when the tool is present.


### FINDING_4: Health gate lacks outer wall-clock deadline around full probe work
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The old shell health gate wrapped the whole probe command in `timeout`, but the direct in-process call only passes timeout to child CLI probes. Work before `_run_probe_command`, such as Cursor keychain `security` calls or Darwin serial-lock waits, can exceed `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=1` and block `run_external_agent()` instead of returning the documented fast-fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Enforce an outer deadline around the full `check_reviewers()` call, or run the probe through a subprocess/thread/future with timeout. Add a test where a blocked pre-probe path returns `health-probe timed out after 1s` within the configured wall-clock limit.


