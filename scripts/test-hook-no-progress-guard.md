# test-hook-no-progress-guard.sh

Offline regression harness for `hook-no-progress-guard.sh`.

Run with `bash scripts/test-hook-no-progress-guard.sh`.

## Primary callers

- `make test-hook-no-progress-guard`
- `make lint` (via the standard hook-test sweep)

## Coverage

Tests cover: no-marker no-op, counter increment on live marker, threshold triggering
breaker arming, UserPromptSubmit block with armed breaker, UserPromptSubmit allow without breaker,
terminal-sentinel release (step completed), `LARCH_NO_PROGRESS_GUARD_DISABLE=1` no-op, Stop
re-entry guard, custom threshold via `LARCH_NO_PROGRESS_GUARD_THRESHOLD`, Step 8 rc sidecar
release, and the additional Step 4 tail / implement Step 7a / Step 6 / Step 5 resume /
Step 5 self-review marker mappings. Symlink sentinels stay live.

Clone-scoping coverage verifies marker-local `CLONE_PATH` preference for both Stop and
UserPromptSubmit, fallback to `.larch-keepalive` when the embedded stamp is absent, and
the fail-safe count/block behavior when both identity sources are unavailable.

See `hook-no-progress-guard.md` for the full invariant set.
