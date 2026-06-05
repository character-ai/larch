## Proposed Design Outline

### Goals
- Stop the degraded-tools gate from falsely reporting `BOTH_DOWN=true` when presence flags arrive empty after ambient shell state is lost across a fresh Bash tool call.
- Make the empty-presence-input bug class loud and self-revealing for every caller, instead of silently normalizing empty to `false`.

### Non-goals
- No change to `DEGRADED` / `BOTH_DOWN` / `CODEX_STATE` / `CURSOR_STATE` classification for valid, non-empty presence inputs.
- No change to the gate's pure-detector contract (never prompts, never blocks; exit 0 valid argv / exit 2 argv error).
- No reviewer or waterfall topology changes.

### Approach sketch
- `/implement` SKILL.md gate block: read the four presence keys from `session-env.sh` via `read-session-env-key.sh --default false` before the `degraded-tools-gate.sh` call — the pattern `implement-bootstrap.sh` already uses.
- `degraded-tools-gate.sh`: detect empty/unset presence (distinct from explicit `false`), emit a loud `larch_err` diagnostic plus a machine KV; keep classification and fail-safe polarity unchanged.
- Shared `external-reviewers.md`: extend the canonical gate procedure to cover skills whose gate runs in a separate block from session-setup — read from the durable session-env file, not only "re-parse stdout in the current block".
- `/design` SKILL.md gate block: read presence keys from the durable sourced env explicitly (consistency hardening).
- `/research` + `/review`: confirmed same-block / safe — no behavior change.
- Regression guard: structural SKILL.md assertion in `test-implement-structure.sh`.

### Surfaces in scope
- `scripts/degraded-tools-gate.sh` (+ sibling `.md`, harness)
- `skills/implement/SKILL.md`, `skills/design/SKILL.md`
- `skills/shared/external-reviewers.md`
- `skills/implement/scripts/test-implement-structure.sh`

### Open questions
- Exact KV name/shape for the empty-input signal (e.g. `PRESENCE_INPUT_EMPTY=true`) — finalize in the plan, refine via review.
- Whether `/research` + `/review` get a structural same-block pin or stay documented-only.
