# scripts/write-session-id.sh — contract

`scripts/write-session-id.sh` is the single-call wrapper around the `uuidgen`-or-fallback session-id snippet that `/implement` Step 0 emits to `$IMPLEMENT_TMPDIR/session-id`. The id pins design-manifest freshness: `read-design-manifest.sh` rejects a manifest whose stored `SESSION_ID` does not match the value in this file.

## Inputs

- `--output PATH` (required) — destination path. Parent directory is `mkdir -p`-ensured.

## Behavior

- If `PATH` already exists and is non-empty, exit 0 without modifying it. This keeps the wrapper idempotent now that `session-setup.sh` creates `session-id` directly.
- If `uuidgen` is on `PATH`, write `uuidgen` output to `PATH`.
- Otherwise fall back to `$(basename $(dirname PATH))` — the session tmpdir basename, which is unique per run and adequate as a freshness key when uuidgen is absent.

## When to update

Update this file when the freshness key needs different semantics (e.g., monotonic counter, hash of repo HEAD + timestamp). The current contract is intentionally minimal; expanding it requires updating `read-design-manifest.sh`'s comparison logic in the same PR.

## Test harness

No sibling regression harness — the wrapper is two lines of shell behind a uuidgen-vs-fallback predicate. Manual smoke verification at write-time covers both paths; CI's shellcheck pass covers syntax regressions.
