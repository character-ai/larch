## Proposed Design Outline

### Goals
- Surface `phase_driver_write_result_env` failures in `step3_loop_persist_envelope` so the orchestrator always receives a usable `STEP3_REVIEW_LOOP_STATUS`.
- Add a final-resort observability guard in `design-step3-review.sh` that degrades gracefully to `panel-failed` when both statuses are empty.
- Eliminate "Reading additional input from stdin..." noise from external CLI subprocesses by adding `</dev/null` to cursor and codex invocations in `launch-review.sh`.

### Non-goals
- Fixing or retrying `phase_driver_write_result_env` itself.
- Changing the plan-review panel flow or voting logic.
- Touching any launcher other than `launch-review.sh` for the stdin fix.

### Approach sketch
- In `review-design-step3-loop.sh` `step3_loop_persist_envelope`: on failure, `emit_kv STEP3_REVIEW_LOOP_STATUS panel-failed` and write a Tool Failures entry to `execution-issues.md`.
- In `design-step3-review.sh`: when both statuses are empty/invalid after sourcing result env, also set `STEP3_REVIEW_LOOP_STATUS=panel-failed` and emit warning to stderr.
- In `launch-review.sh`: add `</dev/null` to the `cursor agent -p` call and both `codex exec` call sites.
- Update sibling `.md` files for touched scripts in the same PR.

### Surfaces in scope
- `skills/design/scripts/review-design-step3-loop.sh`
- `skills/design/scripts/design-step3-review.sh`
- `scripts/launch-review.sh`
- `.md` siblings: `review-design-step3-loop.md`, `design-step3-review.md`, `launch-review.md`

### Open questions
- None.
