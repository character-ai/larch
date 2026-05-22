# scripts/write-session-id.sh — contract

`scripts/write-session-id.sh` is the single-call wrapper around the `uuidgen`-or-fallback session-id snippet that `/implement` Step 0 emits to `$IMPLEMENT_TMPDIR/session-id`. The id is forwarded as `LARCH_TOKEN_SESSION_ID` (and recorded in `session-env.sh`) so token/timing ledgers and hook tmpdir resolution can bind the active run to the correct `claude-implement-*` session root.

## Inputs

- `--output PATH` (required) — destination path. Parent directory is `mkdir -p`-ensured.

## Behavior

- If `PATH` already exists and is non-empty, exit 0 without modifying it. This keeps the wrapper idempotent now that `session-setup.sh` creates `session-id` directly.
- If `uuidgen` is on `PATH`, write `uuidgen` output to `PATH`.
- Otherwise fall back to `$(basename $(dirname PATH))` — the session tmpdir basename, which is unique per run and adequate as a freshness key when uuidgen is absent.

## When to update

Update this file when the session-id semantics need to change (e.g., monotonic counter, hash of repo HEAD + timestamp). The current contract is intentionally minimal; expanding it requires updating the `/implement` Step 0 materialization path and any consumers that assume the current shape in the same PR.

## Test harness

No sibling regression harness — the wrapper is two lines of shell behind a uuidgen-vs-fallback predicate. Manual smoke verification at write-time covers both paths; CI's shellcheck pass covers syntax regressions.
