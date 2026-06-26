## Proposed Design Outline

### Goals
- Remove the hardcoded plan-review panel matrix (Cursor + Codex archetype enumeration) from the loaded `skills/design/SKILL.md` prose.
- Route SKILL readers to the single source: `references/plan-review.md` authority, backed by `topology.tsv` and `python/rendering.py`.
- Preserve every load-bearing Step 3 instruction so panel behavior is byte-for-byte unchanged.

### Non-goals
- No runtime behavior change. Python dispatch already builds the panel manifest.
- No edits to the count source of truth or generated projection (`topology.tsv`, `docs/topology.md`); counts do not change, so no topology regeneration.
- No edits to load-bearing runtime inputs (`scout-plan-archetypes-prompt.txt`) or code (`python/rendering.py`).

### Approach sketch
- In `SKILL.md`, strip the archetype enumeration from three spots: the line-10 opening summary, the Step 3 "IMPORTANT" panel block, and the spawn-order line.
- Replace each with generic phrasing plus a pointer to the `plan-review.md` authority.
- Keep "MUST ALWAYS run / never skip", slowest-first spawn order, and the cross-tool/Claude fallback rules intact.
- Lightly reconcile `references/plan-review.md` so it remains the single prose home the topology rows already designate.
- Verify with `make lint` (agent-lint S030 path pins, drift-prose rule, markdownlint).

### Surfaces in scope
- `skills/design/SKILL.md` — opening summary, Step 3 panel block, spawn-order prose.
- `skills/design/references/plan-review.md` — authority reconcile (light).

### Open questions
- `docs/review-agents.md` also spells the matrix inline (but already links the topology anchors). Default: out of scope, since it is a human-facing consumer catalog, not loaded SKILL prose. Confirm, or pull it in.
