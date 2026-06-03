# scripts/check-reviewers.sh — contract

Runtime health probe for the Codex and Cursor CLIs used by external reviewers and `/implement` Step 2 presence gates.

## Output keys

- `CODEX_BINARY_FOUND=true|false` — whether `command -v codex` succeeded before any skip/probe logic.
- `CURSOR_BINARY_FOUND=true|false` — whether `command -v cursor` succeeded.
- `CODEX_PRESENT=true|false` — whether the Codex runtime probe succeeded (or a fresh TTL stamp said so); `false` when the binary is missing, `--skip-codex-probe` is set, the probe failed, auth retries exhausted, or the probe timed out.
- `CURSOR_PRESENT=true|false` — symmetric for Cursor (includes Darwin `cursor_auth_preflight` short-circuit when it returns 2).
- `CODEX_AVAILABLE` / `CURSOR_AVAILABLE` — backward-compatible aliases for `CODEX_PRESENT` / `CURSOR_PRESENT`.

Downstream docs use `*_BINARY_FOUND=false` vs `*_PRESENT=false` to distinguish "binary not on `PATH`" from "binary present but runtime probe failed / skipped / auth / timeout".

## Flags

- `--skip-codex-probe` — emit `CODEX_PRESENT=false` (and alias) without invoking `codex`; `CODEX_BINARY_FOUND` still reflects `command -v`.
- `--skip-cursor-probe` — same for Cursor.

## Probe behavior (summary)

- Sources `lib-cursor-launcher-common.sh` (which pulls `lib-external-launcher-common.sh`) and `lib-cursor-auth.sh`.
- Env knobs (validated integers; invalid / empty falls back as documented in `docs/configuration-and-permissions.md`):
  - `LARCH_PROBE_TTL_SECONDS` (default `60`) — stamp freshness window; `0` disables stamp cache (always re-probe when the binary exists and the probe is not skipped).
  - `LARCH_PROBE_TIMEOUT_SECONDS` (default `30`; `0` treated as invalid → `30`) — per-attempt wall-clock cap while the background probe PID is alive.
  - `LARCH_EXTERNAL_AUTH_RETRIES` (default `5`; `0` / invalid → `5`) — max auth-classified failures before giving up (`MAX_AUTH_RETRIES` in the script).
- **Cursor**: Darwin serial mutex (`external_serial_lock_acquire` / `external_serial_lock_release_after` with `LARCH_EXTERNAL_SERIAL_LOCK_DELAY`, default `0.5s`); `cursor_auth_preflight` before the probe loop; `cursor_preread_service_token` + `cursor_auth_export_env` (env-based auth — the probe child inherits `CURSOR_API_KEY`, no `--api-key` argv element, issue #3375); private config dir (`cursor_launcher_setup_private_config_dir` / cleanup); probe argv mirrors production Cursor invocations: `cursor agent -p "<wrapped-prompt>" --trust --workspace "$PWD" --model <resolved> …` where `<wrapped-prompt>` is `" /max-mode on. Prompt: Respond with OK"` from `cursor-wrap-prompt.sh` and `<resolved>` comes from `scripts/agent-model-args.sh --tool cursor` (defaults to `composer-2.5`). This makes the probe surface auth/quota errors that are model-specific. `--mode plan` and `--output-format json` remain off — reachability + auth only.
- **Codex**: same mutex pattern on Darwin; probe uses `codex exec --sandbox read-only -C "$PWD" --output-last-message <tmp> <model-args…> -- "Respond with OK"` where `<model-args…>` comes from `scripts/agent-model-args.sh --tool codex --with-effort` (mirrors production reviewer launches in `launch-review.sh`). Intentional asymmetry per `.claude/rules/external-tool-launcher-parity.md`: Codex passes `--with-effort` (effort is meaningful for Codex) while the Cursor probe omits it (Cursor ignores effort). Read-only posture aligned with reviewer launches; no `--add-dir` on the probe.
- **Stamps** (atomic `mktemp` + `mv` under `${TMPDIR:-/tmp}`): `larch-cursor-present-${USER:-larch}.stamp`, `larch-codex-present-${USER:-larch}.stamp`; first line must be exactly `true` or `false` to count as a cache hit.

## Rejected flags

`--probe` is rejected with **exit code 1** and an `unknown argument` message on stderr (historic flag; no alternate mode).

## Test harness

`scripts/test-check-reviewers.sh` — PATH-stubbed binaries, auth-retry matrix, TTL stamp hit/expired, skip flags, invalid env normalization, and `--probe` rejection.

- **Codex probe model-args forwarding**: PATH-stubbed `codex` appends argv to `LARCH_TEST_CODEX_PROBE_ARGV_LOG` (fixture `codex-probe-argv.log`); with `LARCH_CODEX_MODEL=sentinel-model` asserts `CODEX_PRESENT=true` and that the logged argv contains `sentinel-model`.

## Edit-in-sync

| File | Relationship |
|------|----------------|
| `scripts/check-reviewers.sh` | Source of truth |
| `scripts/session-setup.sh` | Parses `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` for `--write-session-env` forwarding |
| `scripts/write-session-env.sh` | Optional `--codex-binary-found` / `--cursor-binary-found` persistence |
| `scripts/session-setup.md` | Contract prose for stdout + session-env keys |
| `skills/shared/external-reviewers.md` | Operator-facing semantics for `*_PRESENT` / `*_BINARY_FOUND` |
| `docs/configuration-and-permissions.md` | Env catalog entries for probe tuning |
