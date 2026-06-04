## Proposed Design Outline

### Goals
- Move the `[DESIGNING]`→`[DESIGNED]` title rename to **right after the architecture-diagram upsert** in `design-publish.sh`, before log publish.
- Drop the rename's `PUBLISH_OK==true` gate so `[DESIGNED]` admission no longer waits on — or can be blocked by — the design-log PR.
- Keep the rename idempotent and best-effort; preserve every other publish-tail behavior.

### Non-goals
- No `/implement` change — it only keys on the `[DESIGNED]` title.
- No change to the publish / security model (`gh pr merge --admin` flow unchanged) → no SECURITY.md change.
- Do **not** move or alter `design_reentry_marker_write` — it stays after publish, gated on `PUBLISH_OK==true` (operator-confirmed).
- Do **not** touch the clarify-path `--state designing` rename or Step 6 cleanup gating (still correctly publish-gated).

### Approach sketch
- In `design-publish.sh`: lift the rename block out of the `if SESSION_ID && PUBLISH_OK==true` block; insert it right after the diagram-upsert block, gated only on `[ -n "$SESSION_ID" ]`.
- Leave the reentry-marker block in place (still gated on `SESSION_ID && PUBLISH_OK==true`); it keeps the `lib-design-reentry-guard.sh` source.
- New publish-tail order: plan-write → diagram upsert → **rename** → log publish → post-publish summary → reentry marker.

### Surfaces in scope
- `skills/design/scripts/design-publish.sh` — the reorder (core).
- `skills/design/scripts/design-publish.md` — ordering invariant + responsibilities (also corrects pre-existing drift: a `--pre-publish-only` render and marker-before-upsert that the code never did).
- `skills/design/scripts/test-design-publish.sh` — ordering + publish-failure rename assertions.
- `scripts/test-design-structure.sh` — add `upsert < rename < publish_log` pin; existing (25)/(15b) stay green.
- `skills/design/SKILL.md` — Step 5c prose: rename no longer `PUBLISH_OK`-gated; responsibilities-order parenthetical.

### Open questions
- None. (Reentry-marker placement confirmed: keep gated on publish.)
