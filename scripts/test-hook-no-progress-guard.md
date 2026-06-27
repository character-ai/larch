# test-hook-no-progress-guard.sh

Offline regression harness for `hook-no-progress-guard.sh`.

Run with `bash scripts/test-hook-no-progress-guard.sh`.

## Primary callers

- `make test-hook-no-progress-guard`
- `make lint` (via the standard hook-test sweep)

## Coverage

Ten tests covering: no-marker no-op, counter increment on live marker, threshold triggering
breaker arming, UserPromptSubmit block with armed breaker, UserPromptSubmit allow without breaker,
terminal-sentinel release (step completed), `LARCH_NO_PROGRESS_GUARD_DISABLE=1` no-op, Stop
re-entry guard, and custom threshold via `LARCH_NO_PROGRESS_GUARD_THRESHOLD`.

See `hook-no-progress-guard.md` for the full invariant set.
