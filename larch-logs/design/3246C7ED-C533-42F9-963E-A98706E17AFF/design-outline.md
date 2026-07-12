## Proposed Design Outline

### Goals
- Add a specialist reviewer archetype that validates code (/review, /implement Step 5) and the /design plan against the parsed architectural guidelines and invariants.
- Stop feeding guidelines/invariants to the other reviewer archetypes; only the compliance specialist (and /design Arch) receives that context.
- Keep per-difficulty panel behavior identical to the existing archetypes.

### Non-goals
- Do not stop feeding guidelines/invariants to the /implement Step 2 coder or the /design plan drafter. Authors still honor them.
- Do not add a new archetype to /design plan review. Augment the existing inline Arch personality instead.
- Do not change the implementer `architectural_acknowledgment` manifest contract.

### Approach sketch
- /review + /implement: new specialist agent file plus a slot in the code-review panel (`config._CODE_REVIEW_ARCHETYPES`); gate the `rendering.py` guidelines feed to that specialist only.
- /design: augment the inline Arch plan-review personality to validate guidelines/invariants compliance and ensure it receives that context.
- Strip the now-dead I-*/G-* carve-out paragraph from the other reviewer templates and regenerate the generated agent files.

### Surfaces in scope
- `python/larch/rendering/rendering.py`
- `python/larch/core/config.py`
- `agents/` (new specialist plus regenerated and hand-edited reviewer files)
- `skills/shared/reviewer-templates.md`, `skills/shared/topology.tsv`
- /design Arch personality prompt source and its rendering path
- scout slug reservation (`python/larch/design/plan_scout.py`, `skills/design/scripts/scout-plan-archetypes-prompt.txt`)
- tests under `python/tests/`

### Open questions
- None. (Slug name, generation vs hand-maintained path, focus_area, and exact Arch wiring are Step 2b decisions.)
