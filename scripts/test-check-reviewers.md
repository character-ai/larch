# scripts/test-check-reviewers.sh — contract

Regression harness for `check-reviewers.sh` runtime probes, auth retries, and TTL stamp cache.

## What it tests

- **Binary detection**: `*_BINARY_FOUND` tracks `command -v` independently of skip flags.
- **Stub happy path**: both tools exit 0 → `*_PRESENT=true`.
- **Absent binaries**: `PATH` without stubs → `*_BINARY_FOUND=false` and `*_PRESENT=false`.
- **Skip flags**: `--skip-codex-probe` / `--skip-cursor-probe` force the corresponding `*_PRESENT=false` without invoking the stub binary; the other tool still probes when its binary is stubbed.
- **Cursor non-auth failure**: stub exits 1 with non-matching stderr → no retry, `CURSOR_PRESENT=false`.
- **Cursor auth retry then success**: stub fails with auth-shaped stderr N−1 times then exits 0 → `CURSOR_PRESENT=true`.
- **Cursor auth exhaustion**: stub always auth-fails within a small `LARCH_EXTERNAL_AUTH_RETRIES` → `CURSOR_PRESENT=false`.
- **Cursor TTL stamp**: fresh stamp `true` + high TTL → cache hit without running failing stub; expired mtime + live TTL → re-probe with success stub.
- **Codex matrix**: success, non-auth failure, auth retry success, auth exhaustion, stamp hit, stamp expired, `--skip-codex-probe`.
- **Env normalization**: invalid `LARCH_PROBE_TTL_SECONDS` and `LARCH_PROBE_TIMEOUT_SECONDS=0` still allow a successful probe with defaults.
- **`--probe`**: rejected with exit code **1** (not 2).

Tests set `LARCH_QUIET_DISABLE=1`, `LARCH_LIB_CURSOR_AUTH_TEST_MODE=1`, `LIB_CURSOR_AUTH_TEST_UNAME=Linux` for Cursor paths so Darwin keychain preflight is skipped deterministically. Each run uses an isolated `TMPDIR` under a scratch directory for stamp isolation.

## Wiring

Target: `make test-harnesses`. Exit 0 on all-pass, exit 1 on any failure.

## Edit-in-sync

| File | Relationship |
|------|----------------|
| `scripts/check-reviewers.sh` | Source of truth for behavior under test |
| `scripts/check-reviewers.md` | Operator contract for the script |
