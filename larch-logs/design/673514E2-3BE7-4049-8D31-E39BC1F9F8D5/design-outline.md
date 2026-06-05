## Proposed Design Outline

### Goals
- Thin the two Step 0b consumption fences (route + init) to capture → emit → branch.
- Move all non-LLM rendering into the drivers: cancel summaries, reentry banner, resume env-refresh, init failure banners.
- Preserve all seven routing outcomes + exit codes; harnesses + `make lint` stay green.

### Non-goals
- No change to clarify-loop logic, already-planned prompt, `ROUTE` verdict set, or driver exit-code contract (0/1/2).
- No new harness files — reframe existing pins only.
- No run-params schema or tier-mapping change.

### Approach sketch
- `design-route.sh`: own `render-final-summary.sh` for `cancel-title-filter` / `cancel-reentry-guard`, compose the reentry banner (MARKER_REMAINING math), and run the resume env-refresh; gain a `--session-id` input.
- `design-init-runparams.sh`: own the contract-drift + env-refresh-failed operator banners (emit STATUS + print message itself).
- SKILL.md Step 0b: collapse both fences to capture → emit driver output → branch only into LLM routes (proceed/clarify/already-planned/resume-continue); cancel/resume branch bodies shrink to "emit driver output + propagate exit".
- Reframe `FINDING_2`-family pins in `test-design-structure.sh` + update `test-step0b-router-flag-recovery.sh` to assert the thin shape and driver ownership.

### Surfaces in scope
- `skills/design/scripts/design-route.{sh,md}`
- `skills/design/scripts/design-init-runparams.{sh,md}`
- `skills/design/SKILL.md` (Step 0b route + init consumption fences)
- `scripts/test-design-structure.sh` (FINDING_2-family), `scripts/test-step0b-router-flag-recovery.sh`

### Open questions
- None.
