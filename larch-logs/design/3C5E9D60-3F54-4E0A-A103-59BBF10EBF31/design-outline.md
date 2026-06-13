## Proposed Design Outline

### Goals
- Reduce Step 0 happy path from 6 Bash calls to 3 (session, route, init).
- Fold `design-step0-degraded.sh` into `design-step0-session.sh`; retire the separate script.
- Update SKILL.md and harness to match the new flow.

### Non-goals
- Changing `design-step0-route.sh` (already absorbs issue fetch and REPO resolution).
- Changing `design-step0-init.sh` (already writes `feature-description.txt`).
- Changing route semantics: cancel, clarify, already-planned, and resume paths unchanged.

### Approach sketch
- Add degraded gate logic to `design-step0-session.sh` after session setup.
- Emit `DEGRADED_PROMPT_REQUIRED=true` only when `needs-degraded-decision`; all other KVs (`STEP0_STATUS`, `DEGRADED`, `BOTH_DOWN`) remain.
- Write `.degraded-tools-gate-prompted` sentinel inside session.sh on auto/one-down paths (unchanged semantics).
- Delete `design-step0-degraded.sh` and `design-step0-degraded.md`.
- Update SKILL.md: remove degraded.sh fence, add inline `DEGRADED_PROMPT_REQUIRED=true` branch after session fence, remove raw `gh issue view` sub-step, simplify 0b.
- Update `test-design-structure.sh`: move degraded-gate assertions to session.sh, remove degraded.sh from wrapper manifest.

### Surfaces in scope
- `skills/design/scripts/design-step0-session.sh`
- `skills/design/scripts/design-step0-degraded.sh` (deleted)
- `skills/design/scripts/design-step0-degraded.md` (deleted)
- `skills/design/SKILL.md`
- `scripts/test-design-structure.sh`

### Open questions
- None.
