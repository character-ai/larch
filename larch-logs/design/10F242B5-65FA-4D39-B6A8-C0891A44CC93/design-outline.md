## Proposed Design Outline

### Goals
- Centralize the settle-wrapper rc dispatch (rc 0/1/10/11/12/13 plus "other non-zero") into one canonical, site-neutral snippet.
- Point all 4 current copies at that single source so the table appears once and cannot drift.
- Preserve runtime behavior at every site (no behavioral change).

### Non-goals
- No logic moved into Python; rc values stay Python-owned (`design_lifecycle.py` emits `POSTPLAN_RC=`).
- No change to rc semantics or to the settle wrapper itself.
- No edits to the unrelated `/implement` dispatch tables or the `design-step35-settle.md` script contract.

### Approach sketch
- Add `skills/design/references/settle-rc-dispatch.md`: the full rc branch list, site-neutral, with rc 0/10/12/13 captured as a small per-caller variant table (Gate B row vs discussion-round2 / Gate A row).
- Replace each inline copy with a short pointer naming its variant row: approval-gates.md (step 8), discussion-rounds.md (Round-2 body), SKILL.md (Gate A + Gate B trailer guards).
- Load the snippet at the point of need via a MANDATORY read directive (lazy, per G-Skill-1).

### Surfaces in scope
- `skills/design/references/settle-rc-dispatch.md` (new)
- `skills/design/references/approval-gates.md`
- `skills/design/references/discussion-rounds.md`
- `skills/design/SKILL.md` (Gate A + Gate B trailer guards)

### Open questions
- None.
