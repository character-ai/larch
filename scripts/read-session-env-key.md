# scripts/read-session-env-key.sh — contract

## Inputs

- `--file PATH` (required, must be **explicitly present**) — session-env file path. **Explicitly empty or unreadable `PATH` is tolerated when `--default` is set**: the default value is emitted on stdout and the script exits 0 (parallel handling for both empty and unreadable file). This lets standalone `/design` and `/review` invocations — where `SESSION_ENV_PATH` is intentionally empty — call the script in their token-ledger rehydration blocks without stderr noise or `set -e` trips. The flag must still be **explicitly present** in argv: an OMITTED `--file` always keeps the usage error and exit 1, even when `--default` is set, so a caller who simply forgot the flag cannot silently get the default and mask caller bugs. When `--default` is NOT set, an empty or unreadable `PATH` keeps the usage error and exit 1.
- `--key KEY` (required) — `KEY` from a `KEY=VALUE` line.
- `--default VALUE` (optional) — value to emit when the key is absent or has an empty value, OR when `--file` is **explicitly** empty / unreadable. When omitted, missing/empty keys produce empty stdout (caller applies its own fallback) and an empty/unreadable `--file` keeps the usage error. An OMITTED `--file` always keeps the usage error regardless of `--default`.

## Output

Single line on stdout containing the resolved value (no `KEY=` prefix).

## When to update

Update this file when the session-env grammar changes (e.g., supporting quoted values, multi-line values), when a new key conventionally needs a default, or when the safe-parsing rule evolves. The "no source / eval" rule is load-bearing: any change that introduces shell evaluation against the file MUST update SECURITY.md and the Cross-Skill Presence Propagation procedure in SKILL.md Step 0 in the same PR.

## Test harness

`scripts/test-session-env-roundtrip.sh` (Makefile target `make test-session-env-roundtrip`, wired via `test-harnesses-1`) covers the awk extraction grammar — including values containing `=`, empty values, trailing `=`, comma-separated KV-list values, and KEY-prefix collisions — together with `scripts/write-session-env.sh`'s `--timing-ledger` validation.
