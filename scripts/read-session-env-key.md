# scripts/read-session-env-key.sh — contract

`scripts/read-session-env-key.sh` is the safe-parsing wrapper that `/implement` Step 2.1 uses to read `CURSOR_HEALTHY` / `GEMINI_HEALTHY` (and similar keys) from `$IMPLEMENT_TMPDIR/session-env.sh` without sourcing the file. The implementation matches the whole `KEY=` prefix on a line and emits everything after the first `=` (parallel to `value="${line#*=}"` in `session-setup.sh`'s caller-env parser); it deliberately does NOT use the legacy `awk -F= '$1=="KEY"{print $2; exit}' FILE` form because that truncates values containing additional `=` characters at the first separator. Sourcing is unsafe because the file's contents originate from environment-probe output; awk-based extraction prevents code execution from a hostile value.

## Inputs

- `--file PATH` (required) — session-env file path. **Empty or unreadable `PATH` is tolerated when `--default` is set**: the default value is emitted on stdout and the script exits 0 (parallel handling for both empty and unreadable file). This lets standalone `/design` and `/review` invocations — where `SESSION_ENV_PATH` is intentionally empty — call the script in their token-ledger rehydration blocks without stderr noise or `set -e` trips. When `--default` is NOT set, an empty or unreadable `PATH` keeps the usage error and exit 1.
- `--key KEY` (required) — `KEY` from a `KEY=VALUE` line.
- `--default VALUE` (optional) — value to emit when the key is absent or has an empty value, OR when `--file` is empty / unreadable. When omitted, missing/empty keys produce empty stdout (caller applies its own fallback) and an empty/unreadable `--file` keeps the usage error.

## Output

Single line on stdout containing the resolved value (no `KEY=` prefix).

## When to update

Update this file when the session-env grammar changes (e.g., supporting quoted values, multi-line values), when a new key conventionally needs a default, or when the safe-parsing rule evolves. The "no source / eval" rule is load-bearing: any change that introduces shell evaluation against the file MUST update SECURITY.md and the Cross-Skill Health Propagation procedure in SKILL.md Step 0 in the same PR.

## Test harness

`scripts/test-session-env-roundtrip.sh` (Makefile target `make test-session-env-roundtrip`, wired via `test-harnesses-1`) covers the awk extraction grammar — including values containing `=`, empty values, trailing `=`, comma-separated KV-list values, and KEY-prefix collisions — together with `scripts/write-session-env.sh`'s `--timing-ledger` validation.
