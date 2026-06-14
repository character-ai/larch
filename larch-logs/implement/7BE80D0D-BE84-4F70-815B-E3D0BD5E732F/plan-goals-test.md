## Goal
Implement issue #4166: [IMPLEMENTING] Health probes and negotiation.

## Implementation Plan
## Plan

## Approach

Port reviewer health and negotiation from retired Bash scripts into `python/agents.py`, register two `agent` CLI verbs, retarget callers and docs, move harness coverage into pytest, and delete the retired script contracts.

- Add Python-owned equivalents for `check-reviewers.sh` and `run-negotiation-round.sh` in `python/agents.py`.
- Keep behavior stable: same `CODEX_*` / `CURSOR_*` KV output, same stamp paths and TTL rules, same skip flags, same Codex env-key vs login stamp split, same Cursor auth preflight behavior, same negotiation exit codes and `RESPONSE_FILE=` envelope.
- Retarget every live caller to `python3 "$PLUGIN_ROOT/python/cli.py" agent check-reviewers` and `agent run-negotiation-round`.
- Retire the 8 Bash files and add them to `python/migrated-scripts.tsv`.
- Replace Bash harness coverage with pytest coverage in `python/test_agents.py`.

## Files to modify/create

### UPDATED: python/agents.py

Add `CheckReviewersResult` and probe helpers near existing agent helper dataclasses/functions.

Implement:

- `check_reviewers(skip_codex_probe=False, skip_cursor_probe=False, probe_timeout_seconds=None, env=None) -> CheckReviewersResult`
- `check_reviewers_main(argv=None) -> int`
- `run_negotiation_round(tool, prompt_file, output, workspace) -> int`
- `run_negotiation_round_main(argv=None) -> int`

For `check_reviewers()`:

- Use `shutil.which("codex")` and `shutil.which("cursor")`.
- Normalize env knobs exactly like Bash:
  - `LARCH_PROBE_TTL_SECONDS`: default `60`, invalid -> `60`, `0` disables reads.
  - `LARCH_PROBE_NEGATIVE_TTL_SECONDS`: default `0`, invalid -> `0`.
  - `LARCH_PROBE_TIMEOUT_SECONDS`: default `30`, invalid or `0` -> `30`.
  - `LARCH_EXTERNAL_AUTH_RETRIES`: default `5`, invalid or `0` -> `5`.
  - `LARCH_EXTERNAL_SERIAL_LOCK_DELAY`: default `0.5`.
- Preserve stamp paths:
  - `${TMPDIR:-/tmp}/larch-cursor-present-${sanitized_user}.stamp`
  - `${TMPDIR:-/tmp}/larch-codex-login-present-${sanitized_user}.stamp`
  - `${TMPDIR:-/tmp}/larch-codex-env-key-present-${sanitized_user}.stamp`
- Preserve stamp read rules:
  - Ignore stale, future-mtime, unreadable, malformed, and disabled stamps.
  - Accept fresh `true`.
  - Accept fresh `false` only when negative TTL is positive and not expired.
- Write stamps atomically with `tempfile.NamedTemporaryFile(delete=False, dir=TMPDIR)` plus `os.replace`.
- For Cursor:
  - Use `cursor_auth_preflight()`, `cursor_preread_service_token()`, and `cursor_auth_export_env()`.
  - Create a private `CURSOR_CONFIG_DIR` temp dir.
  - Copy `~/.cursor/cli-config.json` when present.
  - Run `cursor agent -p <wrapped prompt> --trust --workspace "$PWD" ...`.
  - Use `resolve_model_args("cursor")`.
  - Use `external_serial_lock_acquire("cursor")` and `external_serial_lock_release_after(...)`.
  - Retry only on auth-class failures, up to `LARCH_EXTERNAL_AUTH_RETRIES`.
  - Preserve the preflight `rc == 2` one-shot live probe path.
- For Codex:
  - Create a temp `CODEX_HOME`.
  - Copy `~/.codex/config.toml` when present.
  - Call `_prepare_codex_home()`.
  - Use `resolve_model_args("codex", with_effort=True)`.
  - Add the trusted-project `-c projects."<cwd>".trust_level="trusted"` config.
  - Add `_codex_auth_args()` when `OPENAI_API_KEY` is non-whitespace.
  - Run `codex exec --sandbox read-only -C "$PWD" ... --output-last-message <tmp> -- "Respond with OK"`.
  - Use sidecar output for auth classification.
  - Retry only on auth-class failures.
- Emit, in this order: `CODEX_BINARY_FOUND`, `CURSOR_BINARY_FOUND`, `CODEX_PRESENT`, `CURSOR_PRESENT`, `CODEX_AVAILABLE`, `CURSOR_AVAILABLE`.

For `_external_health_gate()`:

- Replace the subprocess call to `scripts/check-reviewers.sh` with direct `check_reviewers(...)`.
- Preserve: skip-the-other-tool behavior, `LARCH_EXTERNAL_AUTH_RETRIES=1`, later attempts bypassing cache with `LARCH_PROBE_TTL_SECONDS=0`, fail-open on missing or unparseable presence, timeout as unhealthy before retry, retry count and sleep env handling.
- Pass the health-gate timeout as the probe timeout for the single checked tool.

For `run_negotiation_round()`:

- Preserve argparse contract: `--tool codex|cursor`, `--prompt-file`, `--output`, `--workspace`.
- Return: `0` success, `1` usage/missing prompt/model-args failure, `2` reviewer command or Codex auth failure, `3` Cursor preflight failure.
- Remove the previous output file before launch.
- Emit `RESPONSE_FILE=<output>` on success and on exit `2` / `3` paths.
- For Codex: use output-derived `*.events.jsonl` and `*.sidecar` paths, create temp `CODEX_HOME`, copy config, call `_prepare_codex_home()`, use `resolve_model_args("codex")`, add trusted-project config and `_codex_auth_args()`, run `codex exec --full-auto -C <workspace> ... --output-last-message <output> --json -- -` with prompt file as stdin, mirror quota, record usage, clean temp homes on all paths.
- For Cursor: use `resolve_model_args("cursor")`, call `cursor_auth_preflight()`, call `cursor_auth_export_env()`, use serial lock, run `cursor agent -p --force --trust ... --workspace <workspace> <wrapped prompt>` with stdout and stderr merged to output.

### UPDATED: python/cli.py

Register two new verbs in `_REGISTRY`:

- `("agent", "check-reviewers"): ("agents", "check_reviewers_main")`
- `("agent", "run-negotiation-round"): ("agents", "run_negotiation_round_main")`

### UPDATED: python/session_env.py

Replace the subprocess call to `scripts/check-reviewers.sh` with a direct import and call to `agents.check_reviewers()`. Keep existing caller-env override behavior: if caller provided `CODEX_PRESENT`, skip Codex probe and restore caller value; if caller provided `CURSOR_PRESENT`, skip Cursor probe and restore caller value.

### UPDATED: python/test_agents.py

Add tests for `check_reviewers()`: KV output order and aliases, binary-missing behavior, skip flags, invalid env normalization, positive stamp hit, expired stamp miss, negative stamp ignored by default, negative stamp honored when positive, Codex login vs env-key stamp isolation, auth retry on auth-class failure, no retry on non-auth failure, Cursor preflight `rc == 2` one-shot path, private Cursor config cleanup, Codex temp home cleanup, Codex auth setup failure, and health-gate behavior (retries, cache bypass, fail-open, fast-fail).

Add tests for `run_negotiation_round()`: usage errors return `1`, missing prompt returns `1`, Codex success emits `RESPONSE_FILE=`, Codex failure returns `2`, Codex auth setup failure returns `2`, Codex model-arg failure returns `1`, events and sidecar paths match `${OUTPUT_FILE%.txt}` rule, trust config and env-key config args present, temp home cleanup, Cursor preflight failure returns `3`, Cursor command failure returns `2`, Cursor success emits `RESPONSE_FILE=`, `CURSOR_API_KEY` absent from argv.

Update existing `_external_health_gate` tests to mock `agents.check_reviewers()` instead of writing a fake `scripts/check-reviewers.sh`.

### UPDATED: python/test_session_env.py

Update tests that expected `session setup --check-reviewers` to execute the Bash script. Mock or stub `agents.check_reviewers()` directly. Keep assertions for session env writes, caller-provided presence override, skip-probe behavior, and binary-found key emission.

### UPDATED: scripts/lib-external-launcher-common.sh

Retarget all 6 health-gate invocations from `"$script_dir/check-reviewers.sh" "$skip_arg"` to `python3 "$script_dir/../python/cli.py" agent check-reviewers "$skip_arg"`. Preserve `timeout`/`gtimeout` wrapping, `LARCH_EXTERNAL_AUTH_RETRIES=1`, `LARCH_PROBE_TTL_SECONDS=0` on retry attempts, stderr capture for first-attempt diagnostics, and fail-open on unparseable stdout.

### UPDATED: skills/status/scripts/status.sh

Replace `"$PLUGIN_ROOT/scripts/check-reviewers.sh"` with `python3 "$PLUGIN_ROOT/python/cli.py" agent check-reviewers`. Keep current parsing and degraded-tools gate behavior.

### UPDATED: skills/shared/external-reviewers.md

Replace negotiation bash block examples with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent run-negotiation-round ...`. Update prose to name `agent run-negotiation-round`. Preserve exit-code documentation and `RESPONSE_FILE=` contract.

### UPDATED: skills/research/references/validation-phase.md

Update the Codex/Cursor negotiation delegation text so `/research` points to the new CLI verb through `skills/shared/external-reviewers.md`. Do not change validation lane semantics.

### UPDATED: skills/shared/dialectic-protocol.md

Replace fresh presence-check command examples with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent check-reviewers`. Keep the same local availability derivation rules.

### UPDATED: skills/status/SKILL.md

Update the status skill description to say it uses `agent check-reviewers`.

### UPDATED: docs/external-reviewers.md

Update user-facing references from `scripts/check-reviewers.sh` and `scripts/run-negotiation-round.sh` to the new CLI verbs.

### UPDATED: docs/configuration-and-permissions.md

Update the Codex auth inventory and probe tuning section to name `python/cli.py agent check-reviewers` for the probe and `python/cli.py agent run-negotiation-round` for negotiation. Keep env-var behavior unchanged.

### UPDATED: docs/linting.md

Update the codex-exec-auth allowlist prose after `check-reviewers.sh` is removed. Update `make test-check-reviewers` and `make test-run-negotiation-round` descriptions to point at pytest coverage.

### UPDATED: docs/skills.md

Update `/status` prose to name `agent check-reviewers`.

### UPDATED: docs/installation-and-setup.md

Update Cursor auth inventory prose so negotiation names the Python CLI verb.

### UPDATED: scripts/lib-external-launcher-common.md

Update the health-gate contract to name `python3 python/cli.py agent check-reviewers`. Keep the timeout, retry, cache, and diagnostic semantics unchanged.

### UPDATED: scripts/lib-cursor-auth.md

Update caller inventory to replace retired script names with Python CLI verbs or Python functions.

### UPDATED: scripts/external-tool-registry.md

Update the "add a tool" instructions so presence detection lives in `python/agents.py` and the CLI verb.

### UPDATED: scripts/external-tool-registry.sh

Update comments that list `scripts/check-reviewers.sh` as a sourced consumer. No runtime behavior change.

### UPDATED: scripts/test-external-tool-registry.sh

Retarget the registry consistency check from `scripts/check-reviewers.sh` to `python3 "$REPO_ROOT/python/cli.py" agent check-reviewers`. Keep the availability-key assertions.

### UPDATED: scripts/test-lib-external-launcher-common.sh

Update fake helper setup and assertions so the tested health gate stubs `python/cli.py agent check-reviewers`. Keep the health-gate behavior assertions unchanged.

### UPDATED: scripts/test-lib-external-launcher-common.md

Update references from `check-reviewers.sh` to `agent check-reviewers`.

### UPDATED: scripts/test-lib-cursor-auth.md

Remove references to the retired check-reviewers harness from the shard description, or replace them with `make test-check-reviewers`.

### UPDATED: python/lint_codex_exec_auth.py

Remove `scripts/check-reviewers.sh` from `ALLOWED_SHELL_FILES`. Keep `python/agents.py` as the Python allowlist entry.

### UPDATED: python/test_lint_codex_exec_auth.py

Update expected allowlist behavior. Add regression that raw shell `codex exec` in retired script names is not allowlisted.

### UPDATED: python/migrated-scripts.tsv

Append retired paths: `scripts/check-reviewers.{md,sh}`, `scripts/test-check-reviewers.{md,sh}`, `scripts/run-negotiation-round.{md,sh}`, `scripts/test-run-negotiation-round.{md,sh}`.

### UPDATED: Makefile

Retarget `test-check-reviewers` and `test-run-negotiation-round` recipes to focused pytest. Do not remove shard membership.

### REWRITTEN: scripts/check-reviewers.sh

Delete this retired Bash implementation.

### REWRITTEN: scripts/check-reviewers.md

Delete this retired script contract.

### REWRITTEN: scripts/test-check-reviewers.sh

Delete this retired Bash harness.

### REWRITTEN: scripts/test-check-reviewers.md

Delete this retired harness contract.

### REWRITTEN: scripts/run-negotiation-round.sh

Delete this retired Bash implementation.

### REWRITTEN: scripts/run-negotiation-round.md

Delete this retired script contract.

### REWRITTEN: scripts/test-run-negotiation-round.sh

Delete this retired Bash harness.

### REWRITTEN: scripts/test-run-negotiation-round.md

Delete this retired harness contract.

## Edge cases

- A fresh false stamp must still be ignored unless negative TTL is positive.
- Codex env-key and login auth modes must never share a stamp.
- A health-gate retry must bypass a stale false stamp.
- Direct `_external_health_gate()` must still honor the outer timeout.
- Cursor preflight `rc == 2` must not block the one-shot live probe path.
- Model-arg failures must not be remapped to negotiation exit `2`.
- `RESPONSE_FILE=` must stay present on negotiation exit `2` and `3`.
- Missing prompt files must fail before deleting unrelated output.
- Secret values must not appear in argv, sidecars, or pytest failure messages.

## Failure modes

- If Python probe timeout handling diverges from the old `timeout` wrapper, external launches may wait too long before fast-fail.
- If docs retain retired script paths, `lint-retired-scripts` may fail after the manifest update.
- If Makefile targets are removed instead of retargeted, shard and operator workflows may break.
- If tests mock too high, argv regressions for Codex trust config or Cursor env-key secrecy may slip through.

## Testing strategy

Run focused tests first:

- `python3 -m pytest python/test_agents.py -q -k 'check_reviewers or negotiation_round or health_gate'`
- `python3 -m pytest python/test_session_env.py -q -k check_reviewers`
- `python3 -m pytest python/test_lint_codex_exec_auth.py -q`
- `make test-check-reviewers`
- `make test-run-negotiation-round`
- `make test-lib-external-launcher-common`
- `make test-external-tool-registry`
- `make lint-retired-scripts`

Then run repository checks:

- `bash scripts/relevant-checks.sh`

Before finalizing, run a literal-reference audit:

- `grep -R "scripts/check-reviewers\\.sh\\|scripts/run-negotiation-round\\.sh\\|test-check-reviewers\\.sh\\|test-run-negotiation-round\\.sh" -n . --exclude-dir=.git --exclude-dir=larch-logs --exclude=python/migrated-scripts.tsv`

Only `python/migrated-scripts.tsv` and historical logs may retain retired paths.

## Acceptance

- `python3 -m pytest python/test_agents.py -q -k 'check_reviewers or negotiation_round or health_gate'` passes.
- `python3 -m pytest python/test_session_env.py -q -k check_reviewers` passes.
- `python3 -m pytest python/test_lint_codex_exec_auth.py -q` passes.
- `make test-check-reviewers`, `make test-run-negotiation-round`, `make test-lib-external-launcher-common`, `make test-external-tool-registry` pass.
- `make lint-retired-scripts` passes with all 8 retired script paths in `migrated-scripts.tsv`.
- `bash scripts/relevant-checks.sh` passes.
- No live caller still references any retired script path outside `migrated-scripts.tsv` and historical logs.

diff_lines: 3000

## Test plan
(no test plan section in plan-file)
