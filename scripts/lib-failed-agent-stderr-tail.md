# scripts/lib-failed-agent-stderr-tail.sh - contract

Sourced-only library for redacted, bounded stderr tails on failed codex/cursor/claude subprocess exits (#3202).

## Environment

- **`LARCH_FAILED_AGENT_STDERR_TAIL_LINES`** — tail line count (default **30**, chosen in design over issue #3202's 50). **`0`** disables capture and emission. Non-numeric values fall back to **30**.

## Limits

- Fixed **5120** byte ceiling after redaction (`failed_agent_stderr_byte_cap`).
- **`render_failed_agent_stderr_tail`** spools `tail | redact-tmpdir-paths.sh | redact-secrets.sh` to a temp file, then `head -c` from the spool (pipefail-safe).

## Sidecar

- **`write_failed_agent_stderr_tail`** writes `${output_file}.stderr-tail` atomically (`mktemp` + `mv`). Removes stale `${output_file}.stderr-tail` when disabled or empty.

## Signature

- **`failed_agent_stderr_signature`** — heuristic fingerprint (digit runs → `#`, hex `0x…` → `0x#`, tmp/session paths, output basenames normalized). Not semantic; used for collector dedup only.

## Callers

- `scripts/run-external-agent.sh` — mode-aware source via `select_failed_agent_stderr_source`; `emit_failed_agent_stderr_tail_raw` (non-quiet).
- `scripts/collect-agent-results.sh` — batch dedup emit via `larch_err` (quiet-init safe; no raw `>&2` in lib body for write/render).
- `scripts/launch-claude-subprocess.sh` — pre-`.done` tail from `${OUTPUT}.stderr`.
- `scripts/launch-claude-review.sh` — parent fallback from subprocess stderr capture.

## Invariant

No raw `>&2` in this file except inside **`emit_failed_agent_stderr_tail_raw`** (restricted to non-quiet `run-external-agent.sh`).

## Harness

`scripts/test-lib-failed-agent-stderr-tail.sh` — Makefile target `test-lib-failed-agent-stderr-tail`.
