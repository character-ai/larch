# scripts/lib-failed-agent-stderr-tail.sh - contract

Sourced-only library for redacted, bounded stderr tails on failed codex/cursor/claude subprocess exits (#3202). Sources `lib-quiet.sh` for `larch_err`, `sanitize_diagnostic_line`, and quiet-session-safe emission.

## Environment

- **`LARCH_FAILED_AGENT_STDERR_TAIL_LINES`** — tail line count (default **30**, chosen in design over issue #3202's 50). **`0`** disables capture and emission. Non-numeric values fall back to **30**.

## Limits

- Fixed **5120** byte ceiling after redaction (`failed_agent_stderr_byte_cap`).
- **`render_failed_agent_stderr_tail`** spools `tail | redact-tmpdir-paths.sh | redact-secrets.sh` to a temp file, then `head -c` from the spool (pipefail-safe).

## Sidecar

- **`write_failed_agent_stderr_tail`** writes `${output_file}.stderr-tail` atomically (`mktemp` + `mv`). Removes stale `${output_file}.stderr-tail` when disabled or empty.

## Signature

- **`failed_agent_stderr_signature`** — heuristic fingerprint (digit runs → `#`, hex `0x…` → `0x#`, tmp/session paths, output basenames normalized). Not semantic; used for collector dedup only.

## Collector tail resolution

- **`collector_stderr_tail_candidates`** — phase-fallback stems for `.stderr-tail` lookup.
- **`resolve_collector_stderr_tail_file`** — retry / NS-retry / phase `.stderr-tail` preference, then `${reviewer_file}.launch-stderr` on the primary stem only (no ancestor-phase launcher stderr).

## `select_failed_agent_stderr_source`

Optional 4th positional argument `explicit_sink`: in default (non-capture) mode, a non-empty, non-zero-size `explicit_sink` file is preferred before `<output>.sidecar`, `<output>`, and `<output>.diag`. Empty or missing explicit sinks fall back to the legacy order. `--capture-stdout` and `--capture-stdout-only` branches ignore `explicit_sink`.

## Callers

- `scripts/run-external-agent.sh` — mode-aware source via `select_failed_agent_stderr_source` (passes `--stderr-sink` as the explicit sink); `emit_failed_agent_stderr_tail_raw` (non-quiet FD 2).
- `scripts/collect-agent-results.sh` — batch dedup emit via `larch_err`; delegates tail resolution to `resolve_collector_stderr_tail_file`.
- `scripts/launch-claude-subprocess.sh` — pre-`.done` tail from `${OUTPUT}.stderr`; clears stale `${OUTPUT}.stderr-tail` at entry and on success.
- `scripts/launch-claude-review.sh` — parent fallback from subprocess stderr capture; fenced tail via `emit_failed_agent_stderr_tail_larch_err` (quiet-safe).
- `skills/review/scripts/collect-findings.sh` — replay fallback uses `resolve_collector_stderr_tail_file`.

## Emission variants

- **`emit_failed_agent_stderr_tail_raw`** / **`emit_failed_agent_stderr_tail_file_raw`** — direct `>&2` fences (non-quiet `run-external-agent.sh` only).
- **`emit_failed_agent_stderr_tail_larch_err`** — fenced tail via `larch_err` (quiet-init callers).
- **`_emit_failed_agent_stderr_tail_line`** — single sanitized line via `larch_err` or `>&2` fallback.

## Harness

`scripts/test-lib-failed-agent-stderr-tail.sh` — Makefile target `test-lib-failed-agent-stderr-tail`.
