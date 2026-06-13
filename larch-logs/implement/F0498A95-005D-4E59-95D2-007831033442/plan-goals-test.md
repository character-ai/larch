## Goal
Implement issue #4067: [IMPLEMENTING] /design Step 0: fold degraded gate and issue fetch into session/route fences.

## Implementation Plan
## Plan

## Approach

Keep the change narrow:

- Move the existing degraded gate logic from `design-step0-degraded.sh` into `design-step0-session.sh`.
- Run it after `source-env.sh` is written, while the session wrapper still has the reviewer presence KVs from `session setup`.
- Keep `design-step0-route.sh` and `design-step0-init.sh` unchanged. They already own issue fetch, `REPO`, route-state sidecar, and `feature-description.txt`.
- Update `/design` prose so Step 0 happy path has three Bash fences: session, route, init.
- Delete the standalone degraded wrapper and its sibling contract doc.
- Move structural pins from the deleted wrapper to the session wrapper.

## Files to modify/create

### UPDATED: skills/design/scripts/design-step0-session.sh

Add the degraded-tools gate after the successful `session write-design-env` call.

Implementation details:

- Reuse the parsing and stdout filtering from `design-step0-degraded.sh`.
- Invoke `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent degraded-tools-gate --skill design` with `CODEX_PRESENT`, `CURSOR_PRESENT`, `CODEX_BINARY_FOUND`, and `CURSOR_BINARY_FOUND` flags.
- Preserve all emitted gate lines: `DEGRADED_EXPLANATION_BEGIN` / `DEGRADED_EXPLANATION_END`, `DEGRADED=`, `BOTH_DOWN=`, `PRESENCE_INPUT_EMPTY=`, `CODEX_STATE=`, `CURSOR_STATE=`.
- Preserve status behavior:
  - no degraded state: `STEP0_STATUS=ok`
  - one tool down: write `.degraded-tools-gate-prompted`, emit `STEP0_STATUS=degraded-one-down`
  - both down and non-interactive: append warning to `execution-issues.md`, write `.degraded-tools-gate-prompted`, emit `STEP0_STATUS=degraded-both-down-auto`
  - both down and interactive: emit `STEP0_STATUS=needs-degraded-decision` and `DEGRADED_PROMPT_REQUIRED=true`
- Always emit `STEP0_STATUS=...`, `DEGRADED=...`, `BOTH_DOWN=...`.
- Emit `DEGRADED_PROMPT_REQUIRED=true` only for `needs-degraded-decision`.

### REWRITTEN: skills/design/scripts/design-step0-degraded.sh

Delete this file. The session wrapper now owns the gate.

### REWRITTEN: skills/design/scripts/design-step0-degraded.md

Delete this file. The standalone wrapper contract no longer exists.

### UPDATED: skills/design/SKILL.md

Update Step 0 prose and wrapper inventory:

- Remove `design-step0-degraded.sh` and `design-step0-degraded.md` from the wrapper contract inventory.
- In Step 0a, say the session wrapper also runs the degraded-tools gate after session setup.
- Remove the separate degraded-tools gate Bash fence.
- Parse `STEP0_STATUS`, `DEGRADED`, `BOTH_DOWN`, and optional `DEGRADED_PROMPT_REQUIRED` from the session wrapper stdout.
- Keep the `AskUserQuestion` branch for `DEGRADED_PROMPT_REQUIRED=true` and abort through `design-step0-abort-cleanup.sh`.
- Simplify Step 0b: state that `design-step0-route.sh` owns issue fetch, `REPO` resolution, route execution, and route-state stdout; remove prose directing raw `gh issue view` and the separate result-env re-read; keep cancel, clarify, already-planned, and resume semantics unchanged; keep `design-step0-init.sh` as the init fence.

### UPDATED: scripts/test-design-structure.sh

Move degraded gate assertions to the session wrapper:

- Remove assertions that require `design-step0-degraded.sh` in `SKILL.md`.
- Remove wrapper contract pins for the deleted degraded wrapper.
- Add pins on `design-step0-session.sh` for: `agent degraded-tools-gate --skill design`, `STEP0_STATUS=`, `DEGRADED_PROMPT_REQUIRED=true`, `needs-degraded-decision`, `BOTH_DOWN_SEEN`, `degraded-both-down-auto`, `.degraded-tools-gate-prompted`, `LARCH_SKILL_NON_INTERACTIVE`.
- Add a negative pin that `SKILL.md` no longer references `design-step0-degraded.sh`.
- Keep existing route, init, and other pins unchanged.

## Edge cases

- **Interactive both-down**: session emits the explanation and `DEGRADED_PROMPT_REQUIRED=true`; prompt asks Continue / Abort.
- **Non-interactive both-down**: session logs the warning, writes the sentinel, and proceeds degraded.
- **One-down degraded**: session writes the sentinel and proceeds without prompting.
- **Re-entry after prompt**: existing sentinel prevents a second prompt.
- **Empty presence input**: session appends the rehydration warning to `execution-issues.md`.
- **Session setup failure**: do not run the degraded gate; keep the current setup failure handling.

## Failure modes

- If `agent degraded-tools-gate` writes unexpected stdout, only the allowlisted gate lines should pass through.
- If `BOTH_DOWN` is missing or malformed in a degraded state, prefer the safe prompt path.
- If the temp stdout capture cannot be created, abort with a clear Step 0 session error.

## Testing strategy

Run targeted checks:

- `bash -n skills/design/scripts/design-step0-session.sh`
- `bash scripts/test-design-structure.sh`
- `bash scripts/relevant-checks.sh`

Manual smoke checks:

- healthy tools: session emits `STEP0_STATUS=ok`; next fence is route.
- one tool down: session emits `degraded-one-down`; no separate degraded fence.
- both down interactive: session emits `DEGRADED_PROMPT_REQUIRED=true`.
- both down non-interactive: session emits `degraded-both-down-auto`.
- issue path: Step 0 uses `design-step0-session.sh`, `design-step0-route.sh`, `design-step0-init.sh`.

## Acceptance

- Issue path reaches Step 0c after three Bash calls (session, route, init); no raw `gh` invocation remains in Step 0 prose.
- Degraded prompt, abort-cleanup, and all route branches behave exactly as today.
- `test-design-structure.sh` passes with degraded gate assertions on `design-step0-session.sh`.

diff_lines: 180

## Test plan
(no test plan section in plan-file)
