# scripts/check-reviewers.sh — contract

Checks external reviewer (Codex/Cursor, plus opt-in Gemini) binary availability and optional health probe.

## Probe acceptance rule

With `--probe`, sends `"Respond with OK"` to each available tool with a 60-second timeout. The probe reply is normalized: all whitespace is stripped (`tr -d '[:space:]'`), then lowercased (`tr '[:upper:]' '[:lower:]'`). The result must equal exactly `"ok"` (case-insensitive exact match, NOT substring). This accepts `OK`, `ok`, `Ok`, `oK` (with any surrounding whitespace) and rejects empty output, error messages, verbose responses, and words containing "ok" as a substring (e.g., `token`, `broken`, `NotOK`). Gemini probes first parse the CLI JSON envelope with `jq -r '.response // empty'`; `.error` or missing `.response` fails the probe. The Gemini probe's `-m` argument resolves with the same precedence as `scripts/launch-gemini-review.sh`: `LARCH_GEMINI_MODEL` then `CLAUDE_PLUGIN_OPTION_GEMINI_MODEL`, defaulting to `gemini-2.5-pro` — so probe and reviewer always exercise the same model.

Failed probes are retried up to 2 additional times (3 total attempts) with a 10-second sleep between attempts, applying the same acceptance rule each round. Each attempt only re-probes tools that are still unhealthy; healthy tools settle and stay healthy. Skipped tools (`--skip-codex-probe` / `--skip-cursor-probe` / `--skip-gemini-probe`) are settled as `*_HEALTHY=false` immediately and are never probed. The retry loop is data-driven over the selected tool list so adding a reviewer does not require pairwise `STILL_NEEDED` logic.

**Worst-case duration**: when both tools stay unresponsive across all 3 attempts, the upper bound is roughly 3 × 120s waits (per-attempt grace) + 2 × 10s inter-attempt sleeps ≈ 380s (~6m20s). This is up from the prior single-retry upper bound of ~240s. Callers with hard wallclock budgets (interactive timeouts, CI job limits) should account for this.

## Output keys

- `CODEX_AVAILABLE=true|false` — binary exists on PATH
- `CURSOR_AVAILABLE=true|false` — binary exists on PATH
- `GEMINI_AVAILABLE=true|false` — binary exists on PATH (only with `--include-gemini`)
- `CODEX_HEALTHY=true|false` — (only with `--probe`) exit 0 and normalized output == "ok"
- `CURSOR_HEALTHY=true|false` — (only with `--probe`) exit 0 and normalized output == "ok"
- `GEMINI_HEALTHY=true|false` — (only with `--probe --include-gemini`) exit 0 and JSON `.response` normalizes to "ok"
- `CODEX_PROBE_ERROR=<msg>` — (only on probe failure) diagnostic message
- `CURSOR_PROBE_ERROR=<msg>` — (only on probe failure) diagnostic message
- `GEMINI_PROBE_ERROR=<msg>` — (only on probe failure) diagnostic message

## Flags

- `--probe` — run health probes (without this, only binary availability is checked)
- `--include-gemini` — include Gemini availability and probe output; callers omit it to preserve the legacy Codex+Cursor surface
- `--skip-codex-probe` — skip Codex probe (marks CODEX_HEALTHY=false)
- `--skip-cursor-probe` — skip Cursor probe (marks CURSOR_HEALTHY=false)
- `--skip-gemini-probe` — skip Gemini probe (marks GEMINI_HEALTHY=false)

## Test harness

`scripts/test-check-reviewers.sh` — regression tests for the probe acceptance logic using fixture replies and a stubbed Gemini integration probe. Covers positive cases (OK, ok, Ok, whitespace variants), negative cases (empty, token, broken, NotOK, error messages), Gemini `.response`, Gemini `.error`, and missing-`jq` fail-closed behavior. Wired into `make test-harnesses`.

## Edit-in-sync

| File | Relationship |
|------|-------------|
| `scripts/session-setup.sh` | Orchestrates probe invocation via `--check-reviewers`; opts into Gemini via `--check-gemini-reviewer`; parses health keys |
| `scripts/run-external-agent.sh` | Wrapper with timeout for probe subprocess |
| `scripts/wait-for-reviewers.sh` | Sentinel polling for probe completion |
| `skills/shared/external-reviewers.md` | Documents the two-key rule (`*_AVAILABLE` + `*_HEALTHY`) |
| `scripts/test-check-reviewers.sh` | Regression harness for acceptance logic |
