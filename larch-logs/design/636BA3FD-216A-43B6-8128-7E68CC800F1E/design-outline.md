## Proposed Design Outline

### Goals
- Remove em-dashes from the Step 1d.7 auto-approve breadcrumb literal in `skills/design/SKILL.md:249`.
- Remove em-dashes from all operator-visible warning and skip-breadcrumb strings in `python/larch/design/design_step5b.py`.

### Non-goals
- Do not touch machine-parsed tokens, sentinels, or KEY=value grammar.
- Do not edit `references/design-outline.md` or `references/finalize-step5.md` (out of scope; coordinated with issue #6294).
- Do not change any logic, exit codes, or control flow.

### Approach sketch
- In `SKILL.md` line 249: replace `— auto-approved` with `: auto-approved` in the breadcrumb string.
- In `design_step5b.py` `_STEP5B_SKIP_BREADCRUMBS` dict (lines 69-73): replace each ` — ` separator with `; `.
- In `design_step5b.py` warning print strings (lines 168, 187, 240, 269): replace each ` — ` separator with `; `.

### Surfaces in scope
- `skills/design/SKILL.md` (line 249 breadcrumb literal)
- `python/larch/design/design_step5b.py` (lines 69-73 and 168-269)

### Open questions
- None.
