## Decision 1: Behavior preservation vs. cleanup
- **Question**: Strict behavior-preserving extraction, or allow low-risk inline cleanups?
- **Resolution**: Allow low-risk cleanups. Preserve all observable outputs (routing decisions, GitHub mutations, artifacts) but fix small latent issues surfaced during extraction inline — specifically consolidate redundant `write-design-current-env.sh` calls and tighten idempotent-on-replay rename/run-params.
- **Source**: user

## Decision 2: Test + doc artifact scope
- **Question**: Which verification/cross-cutting artifacts ship in this PR?
- **Resolution**: Ship the driver `.sh` scripts + mandatory `.md` doc siblings. Write NO new driver test harnesses (no `test-design-route.sh` / `test-design-init-runparams.sh`). DO make the minimal edits to EXISTING harnesses so CI stays green: `scripts/test-design-structure.sh` anchors, the `#3008` jq-merge anchor, and `scripts/test-step0b-router-flag-recovery.sh`.
- **Source**: user

## Decision 3: Driver granularity (2-driver split)
- **Question**: One combined driver or two?
- **Resolution**: Two drivers, split around the in-region `AskUserQuestion` gates: `design-route` (pre-gate: resume-detect → title-eligibility → reentry-guard → single `ROUTE=` verdict) and `design-init-runparams` (post-gate: tier-resolve → `[DESIGNING]` rename → env-refresh → `write-run-params.sh` → router-flag merge).
- **Source**: codebase (issue #3245 "Split by the in-region gates")

## Decision 4: LLM / gate boundary (must-not-move)
- **Question**: What stays in the orchestrator?
- **Resolution**: The clarify-loop and already-planned `AskUserQuestion` gates, and the verbal-create `/larch:issue` Skill call, MUST stay in the orchestrator. Drivers only emit verdicts/state; they never prompt the user or create issues.
- **Source**: codebase (issue #3245 "Must not")

## Decision 5: Network (gh) calls allowed inside drivers
- **Question**: May the phase drivers make network `gh` calls?
- **Resolution**: Yes. The `[DESIGNING]` rename (`tracking-issue-write.sh`) and resume `design-pause-load.sh` are explicitly part of the driver regions per the issue, so network `gh` calls inside drivers are in-bounds. Only `AskUserQuestion` + `/larch:issue` are the LLM boundary.
- **Source**: codebase (issue #3245 "Region owned" / "Stops before")

## Decision 6: Non-goals
- **Question**: What is explicitly out of scope?
- **Resolution**: Do NOT touch the rank-1 Step 3 driver (`run-step3-review.sh`, #3244, already landed) or other umbrella #3133 siblings. Do NOT change the public `/design` flag contract or the `run-params.json` v3 schema. Do NOT move any `AskUserQuestion` gate or `/larch:issue` into a script. Per-round velocity (L3 / #2672) stays deferred.
- **Source**: codebase (issue #3245 / umbrella #3133 / flags.md)

## Decision 7: Phase-driver convention to reuse
- **Question**: What pattern must the new drivers follow?
- **Resolution**: Reuse the rank-1 convention: `set -euo pipefail`, source `lib-phase-driver.sh`, `larch_quiet_init`, `fail()` → exit 2 for config errors, argv parsing, write a result `.env` via `phase_driver_write_result_env` (atomic, symlink-refusing) and emit `emit_kv` KV lines on stdout for the orchestrator to parse. Exit codes: 0=ok, 1=op-failure, 2=config error. Rank-1 dependency (#3244) is landed and confirmed in the working tree.
- **Source**: codebase (`skills/design/scripts/run-step3-review.sh`, `lib-phase-driver.sh`)
