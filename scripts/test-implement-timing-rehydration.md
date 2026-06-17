# test-implement-timing-rehydration.sh

Structural `/implement` telemetry harness. The invariant is wrapper-owned rehydration: SKILL.md Bash fences must not inline `session read-key` triplets or direct token/timing ledger calls.

## Checks

- Reject stale two-key exports in `skills/implement/SKILL.md`.
- Reject inline telemetry/read-key commands inside SKILL.md Bash fences.
- Require key wrappers (`step-2-entry.sh`, `step-5-resume.sh`, `step-18.sh`) to resolve `LARCH_TIMING_LEDGER` and mark timing with `LARCH_TIMING_SKILL=implement`.
- Require plugin-rooted Bash fences to carry the canonical source guard, export `IMPLEMENT_TMPDIR`, and preserve pre-bootstrap awk fallbacks.
- Pin #3425 ordering inside `step-18.sh`: closing marks happen before teardown, with exactly two SKILL.md invocations.
- Pin the `step-5-resume.sh` round-timing duplicate probe so it does not use bare `exit found` and returns success when the row exists.

## Caller

`make test-implement-timing-rehydration` and its Makefile shard.
