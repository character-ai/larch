# scripts/check-reviewers.sh — contract

Checks external reviewer (Codex/Cursor) binary availability and optional health probe. Gemini probe removed in #1720 (Part 1) — it ran with workspace-write access and modified the working tree. `session-setup.sh` hard-codes `GEMINI_HEALTHY=false` / `GEMINI_AVAILABLE=false` unconditionally.

## Tool registry

The script sources `scripts/external-tool-registry.sh` for the canonical external-tool iteration list, using a fail-closed source guard and sentinel check. It also sources `scripts/lib-external-launcher-common.sh` for the shared `external_serial_lock_acquire` / `external_serial_lock_release_after` helpers — each probe spawn acquires the per-tool Darwin serial lock (same `/tmp/larch-<tool>-serial-${USER}.lock` path the production launchers use) so concurrent health probes do not race each other on the macOS keychain. The probe set covers Codex and Cursor; Gemini is skipped in the TOOLS loop regardless of registry contents. The Codex probe argv mirrors the implementer launcher (`scripts/launch-codex-implement.sh`) by passing `--add-dir "$PROBE_DIR"`; this exercises the writable-roots flag production uses so a Codex build that rejects `--add-dir` fails the probe rather than failing later at `/implement` Step 2 spawn with worse diagnostics. The Codex probe also reads `agent-model-args.sh --tool codex` line-token stdout into `CODEX_MODEL_ARGS` (without `--with-effort`, matching `scripts/run-negotiation-round.sh`'s lightweight choice) so invalid `LARCH_CODEX_MODEL` / `CLAUDE_PLUGIN_OPTION_CODEX_MODEL` (blank, whitespace-only, or `[[:cntrl:]]`-bearing) is rejected at probe time with the same rules production launchers apply. The Cursor probe argv mirrors `scripts/launch-review.sh --tool cursor`'s production argv shape: it reads `agent-model-args.sh` line-token stdout into `CURSOR_MODEL_ARGS`, sources `scripts/lib-cursor-auth.sh`, and inserts `"${CURSOR_AUTH_ARGS[@]}"` between the model-args array and `--workspace`. `cursor_auth_preflight` is INTENTIONALLY NOT invoked from the probe. If model-args validation fails, the probe writes a failure sentinel without invoking Cursor.

Per-tool getters/setters and `start_probe` arms remain explicit for Bash 3.2 portability, harness stability, and to avoid silent corruption under indirect expansion. Each switch helper has a defensive `*)` `internal error: unsupported reviewer tool: <id>` arm. Adding a new external tool requires both a registry update and a per-tool branch in every switch helper plus `start_probe`; `scripts/test-external-tool-registry.sh` walks every registry entry to catch missed branches.

Output keys (`CODEX_AVAILABLE`, `CURSOR_AVAILABLE`, `CODEX_HEALTHY`, etc.) remain stable for normal probe classification. A wait infrastructure failure adds `WAIT_INFRA_ERROR=<sanitized>` and emits every available tool's `*_HEALTHY=false` so downstream gates fail closed. The value side of `WAIT_INFRA_ERROR=` may contain `=` characters; `session-setup.sh` parses by splitting on the first `=` only.

## Probe acceptance rule

With `--probe`, sends `"Respond with OK"` to each available tool with a 60-second timeout. The probe reply is normalized: all whitespace is stripped (`tr -d '[:space:]'`), then lowercased (`tr '[:upper:]' '[:lower:]'`). The result must equal exactly `"ok"` (case-insensitive exact match, NOT substring). This accepts `OK`, `ok`, `Ok`, `oK` (with any surrounding whitespace) and rejects empty output, error messages, verbose responses, and words containing "ok" as a substring (e.g., `token`, `broken`, `NotOK`). The Cursor probe uses `--output-format json`; the reply text lives at `.result`; `.error` fails the probe.

Failed probes are retried up to 2 additional times (3 total attempts) with a 3-second sleep between attempts. Each attempt only re-probes tools that are still unhealthy. Skipped tools (`--skip-codex-probe` / `--skip-cursor-probe`) are settled as `*_HEALTHY=false` immediately. Probe classification has three outcomes: healthy, unhealthy probe, and wait infrastructure error. The infrastructure-error path covers invalid wait config and non-zero `wait-for-reviewers.sh` exits.

**Worst-case duration**: when both tools stay unresponsive across all 3 attempts, the upper bound is roughly 3 × 120s waits (per-attempt grace) + 2 × 3s inter-attempt sleeps ≈ 366s (~6m6s).

## Output keys

- `CODEX_AVAILABLE=true|false` — binary exists on PATH
- `CURSOR_AVAILABLE=true|false` — binary exists on PATH
- `CODEX_HEALTHY=true|false` — (only with `--probe`) exit 0 and normalized output == "ok"
- `CURSOR_HEALTHY=true|false` — (only with `--probe`) exit 0 and normalized output == "ok"
- `CODEX_PROBE_ERROR=<msg>` — (only on probe failure) diagnostic message
- `CURSOR_PROBE_ERROR=<msg>` — (only on probe failure) diagnostic message
- `WAIT_INFRA_ERROR=<msg>` — (only when wait infrastructure failed) diagnostic message; paired with `*_HEALTHY=false` for each available tool. The value may contain `=` characters; consumers split on the first `=` only.

## Flags

- `--probe` — run health probes (without this, only binary availability is checked)
- `--skip-codex-probe` — skip Codex probe (marks CODEX_HEALTHY=false)
- `--skip-cursor-probe` — skip Cursor probe (marks CURSOR_HEALTHY=false)
- `--artifact-dir DIR` — accepted for backward compatibility; ignored

## Test harness

`scripts/test-check-reviewers.sh` — regression tests for the probe acceptance logic using fixture replies. Covers positive cases (OK, ok, Ok, whitespace variants), negative cases (empty, token, broken, NotOK, error messages), Cursor JSON output, the wait preflight infrastructure-error contract (`WAIT_INFRA_ERROR`, fail-closed `*_HEALTHY=false`, value-side `=`, no retry loop, no sleeping probe wrapper launch). Wired into `make test-harnesses`.

## Edit-in-sync

| File | Relationship |
|------|-------------|
| `scripts/session-setup.sh` | Orchestrates probe invocation via `--check-reviewers`; hard-codes GEMINI_HEALTHY=false; parses health keys |
| `scripts/run-external-agent.sh` | Wrapper with timeout for probe subprocess |
| `scripts/wait-for-reviewers.sh` | Sentinel polling for probe completion |
| `skills/shared/external-reviewers.md` | Documents the two-key rule (`*_AVAILABLE` + `*_HEALTHY`) |
| `scripts/test-check-reviewers.sh` | Regression harness for acceptance logic |
| `scripts/lib-cursor-auth.sh` | Cursor auth-argv builder + Darwin-gated keychain preflight; sourced for the Cursor probe argv (`cursor_auth_argv` only — preflight not invoked) |

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
