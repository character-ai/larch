## Proposed Design Outline

### Goals
- Extract the Step 5c publish tail (current items 4–11) into one foreground driver `design-publish.sh`.
- Encode ordering invariants in code: 5b-before-5c precondition, reentry-marker before publish/rename, `[DESIGNED]` rename only when `SESSION_ID` set and `PUBLISH_OK=true`.
- Pure prose→code extraction: preserve every existing branch, skip condition, and machine output. No behavior change.

### Non-goals
- No change to compose, the validator gate, or redaction — they stay prompt-side (items 1–3).
- No change to cancellation-path Final-summary callsites (Step 0b / 2b.5 / 3.6) or the other umbrella #3133 pieces.
- No new publish / rename / summary semantics.

### Approach sketch
- New `design-publish.sh` mirrors `design-init-runparams.sh`: `lib-phase-driver.sh`, result-env, `emit_kv`, exit 2/1/0, Bash 3.2-safe.
- Driver argv: `--design-tmpdir --issue --session-id --claude-pid [--repo]`; reads `composed-plan.redacted.md`, `run-params.json`, architecture artifacts from `$DESIGN_TMPDIR`.
- On plan-write failure the driver renders the `failed-plan-write` summary and returns `PLAN_WRITE_OK=false`; orchestrator emits `final-summary.md` verbatim once afterward (uniform single emit point).
- SKILL.md Step 5c collapses items 4–11 into the single driver call; items 1–3 (compose/validate/redact) unchanged.
- `test-design-structure.sh` gains `design-publish.sh` structural pins (mirror the `design-init-runparams.sh` FINDING checks); add `test-design-publish.sh` offline harness.

### Surfaces in scope
- `skills/design/scripts/design-publish.sh` + `design-publish.md`
- `skills/design/scripts/test-design-publish.sh` + `test-design-publish.md`
- `skills/design/SKILL.md` (Step 5c, Step 5d, helper-contracts list)
- `scripts/test-design-structure.sh`
- `docs/` prose referencing the old Step 5c sequence (drift grep)

### Open questions
- None. The three driver-contract forks (boundary, failure-summary ownership, 5b enforcement) were resolved in Round 1.
