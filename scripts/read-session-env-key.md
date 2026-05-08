# scripts/read-session-env-key.sh — contract

`scripts/read-session-env-key.sh` is the safe-parsing wrapper that `/implement` Step 2.1 uses to read `CURSOR_HEALTHY` / `GEMINI_HEALTHY` (and similar keys) from `$IMPLEMENT_TMPDIR/session-env.sh` without sourcing the file. The implementation matches the whole `KEY=` prefix on a line and emits everything after the first `=` (parallel to `value="${line#*=}"` in `session-setup.sh`'s caller-env parser); it deliberately does NOT use the legacy `awk -F= '$1=="KEY"{print $2; exit}' FILE` form because that truncates values containing additional `=` characters at the first separator. Sourcing is unsafe because the file's contents originate from environment-probe output; awk-based extraction prevents code execution from a hostile value.

## Inputs

- `--file PATH` (required) — session-env file path. Must be readable.
- `--key KEY` (required) — `KEY` from a `KEY=VALUE` line.
- `--default VALUE` (optional) — value to emit when the key is absent or has an empty value. When omitted, missing/empty keys produce empty stdout (caller applies its own fallback).

## Output

Single line on stdout containing the resolved value (no `KEY=` prefix).

## When to update

Update this file when the session-env grammar changes (e.g., supporting quoted values, multi-line values), when a new key conventionally needs a default, or when the safe-parsing rule evolves. The "no source / eval" rule is load-bearing: any change that introduces shell evaluation against the file MUST update SECURITY.md and the Cross-Skill Health Propagation procedure in SKILL.md Step 0 in the same PR.

## Test harness

`scripts/test-session-env-roundtrip.sh` (Makefile target `make test-session-env-roundtrip`, wired via `test-harnesses-1`) covers the awk extraction grammar — including values containing `=`, empty values, trailing `=`, comma-separated KV-list values, and KEY-prefix collisions — together with `scripts/write-session-env.sh`'s `--timing-ledger` validation.
