# scripts/check-reviewers.sh — contract

Checks external reviewer (Codex/Cursor) binary availability and optional health probe.

## Probe acceptance rule

With `--probe`, sends `"Respond with OK"` to each available tool with a 60-second timeout. The probe reply is normalized: all whitespace is stripped (`tr -d '[:space:]'`), then lowercased (`tr '[:upper:]' '[:lower:]'`). The result must equal exactly `"ok"` (case-insensitive exact match, NOT substring). This accepts `OK`, `ok`, `Ok`, `oK` (with any surrounding whitespace) and rejects empty output, error messages, verbose responses, and words containing "ok" as a substring (e.g., `token`, `broken`, `NotOK`).

Failed probes are retried up to 2 additional times (3 total attempts) with a 10-second sleep between attempts, applying the same acceptance rule each round. Each attempt only re-probes tools that are still unhealthy; healthy tools settle and stay healthy. Skipped tools (`--skip-codex-probe` / `--skip-cursor-probe`) are settled as `*_HEALTHY=false` immediately and are never probed.

**Worst-case duration**: when both tools stay unresponsive across all 3 attempts, the upper bound is roughly 3 × 120s waits (per-attempt grace) + 2 × 10s inter-attempt sleeps ≈ 380s (~6m20s). This is up from the prior single-retry upper bound of ~240s. Callers with hard wallclock budgets (interactive timeouts, CI job limits) should account for this.

## Output keys

- `CODEX_AVAILABLE=true|false` — binary exists on PATH
- `CURSOR_AVAILABLE=true|false` — binary exists on PATH
- `CODEX_HEALTHY=true|false` — (only with `--probe`) exit 0 and normalized output == "ok"
- `CURSOR_HEALTHY=true|false` — (only with `--probe`) exit 0 and normalized output == "ok"
- `CODEX_PROBE_ERROR=<msg>` — (only on probe failure) diagnostic message
- `CURSOR_PROBE_ERROR=<msg>` — (only on probe failure) diagnostic message

## Flags

- `--probe` — run health probes (without this, only binary availability is checked)
- `--skip-codex-probe` — skip Codex probe (marks CODEX_HEALTHY=false)
- `--skip-cursor-probe` — skip Cursor probe (marks CURSOR_HEALTHY=false)

## Test harness

`scripts/test-check-reviewers.sh` — regression tests for the probe acceptance logic using fixture replies. Covers positive cases (OK, ok, Ok, whitespace variants) and negative cases (empty, token, broken, NotOK, error messages). Wired into `make test-harnesses`.

## Edit-in-sync

| File | Relationship |
|------|-------------|
| `scripts/session-setup.sh` | Orchestrates probe invocation via `--check-reviewers`; parses health keys |
| `scripts/run-external-agent.sh` | Wrapper with timeout for probe subprocess |
| `scripts/wait-for-reviewers.sh` | Sentinel polling for probe completion |
| `skills/shared/external-reviewers.md` | Documents the two-key rule (`*_AVAILABLE` + `*_HEALTHY`) |
| `scripts/test-check-reviewers.sh` | Regression harness for acceptance logic |
