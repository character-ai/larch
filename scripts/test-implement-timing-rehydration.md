# test-implement-timing-rehydration.sh

Structural `/implement` telemetry harness. The invariant is wrapper-owned rehydration: SKILL.md Bash fences must not inline `session read-key` triplets or direct token/timing ledger calls.

## Checks

- Reject stale two-key exports in `skills/implement/SKILL.md`.
- Reject inline telemetry/read-key commands inside SKILL.md Bash fences.
- Require key wrappers (`step-2-entry.sh`, `step-5-resume.sh`, `step-18-finalize.sh`) to resolve `LARCH_TIMING_LEDGER` and mark timing with `LARCH_TIMING_SKILL=implement`.
- Require plugin-rooted Bash fences to carry the canonical source guard and preserve pre-bootstrap awk fallbacks.
- Pin #3425 ordering inside `step-18-finalize.sh`: closing marks happen before teardown, with exactly one SKILL.md invocation.

## Caller

`make test-implement-timing-rehydration` and its Makefile shard.
