## Proposed Design Outline

### Goals
- Extract the Step 3 plan-review orchestrator glue (~210 lines across 2 fences) into a new `run-step3-review.sh`, mirroring `run-step2-dispatch.sh`.
- Establish a shared **Bash** phase-driver foundation (`lib-phase-driver.sh`) that umbrella #3133's later 5 drivers reuse.
- Shrink SKILL.md Step 3 to: invoke the driver, read one normalized result KV set, dispatch gates/branches.

### Non-goals
- No `--resume-from` flag. Preserve existing `.completed/step-3` + `review-round-count.txt` idempotency.
- No change to `plan-review-loop.sh` internals or observable Step 3 behavior (LOOP_STATUS values, branch outcomes, artifacts).
- No absorption of Gate B, semantic finding dedup (#6), or the `main-agent-vote-required` adjudication — those stay in the orchestrator.
- No design of the other 5 umbrella drivers.

### Approach sketch
- `run-step3-review.sh` owns: cap entry guard, HARD round-cursor read/advance, the `plan-review-loop.sh` call, result-env parse + stdout-KV fallback, LOOP_STATUS normalization, round-count persist/rollback. Emits one KV set.
- `lib-phase-driver.sh` holds common helpers: session-env KV reader, `fail`/`usage`, quiet `emit_kv`, result-env emit/parse.
- Orchestrator keeps gate hand-back: driver emits status → orchestrator runs Gate B / dedup / vote → re-invokes.

### Surfaces in scope
- `skills/design/scripts/run-step3-review.sh` (+ `.md` + `test-run-step3-review.sh`)
- `skills/design/scripts/lib-phase-driver.sh` (+ `.md` + unit harness)
- `skills/design/SKILL.md` Step 3
- `scripts/test-design-structure.sh`, `.claude/rules/launcher-argv-test-coverage.md`, `Makefile`

### Open questions
- Shared-lib placement: `skills/design/scripts/` (umbrella is /design-scoped) vs root `scripts/`. Recommend `skills/design/scripts/`; revisit if /implement drivers adopt it.
- Bash lib now overrides the issue's "language deferred" note (your Round 1 call); re-homing to the Python infra may be needed later.
