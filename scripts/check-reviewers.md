# scripts/check-reviewers.sh — contract

Presence-only probe for external reviewer binaries.

## Output Keys

- `CODEX_PRESENT=true|false`
- `CURSOR_PRESENT=true|false`
- `CODEX_AVAILABLE=true|false`
- `CURSOR_AVAILABLE=true|false`

`*_AVAILABLE` is a backward-compatible alias for `*_PRESENT`.

## Flags

- `--skip-codex-probe` skips Codex presence detection and emits `CODEX_PRESENT=false`.
- `--skip-cursor-probe` skips Cursor presence detection and emits `CURSOR_PRESENT=false`.

There is no runtime health probe. `--probe` is intentionally rejected.

## Test Harness

`scripts/test-check-reviewers.sh` covers present, absent, skip-flag, and rejected-`--probe` behavior.
