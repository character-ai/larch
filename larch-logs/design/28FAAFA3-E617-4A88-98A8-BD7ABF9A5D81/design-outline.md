## Proposed Design Outline

### Goals
- One `plan_grammar.py` owns plan-format grammar: heading regexes, trailer key set, trailer composition, and section iteration.
- Repoint the six duplicated parser sites to it; adding a trailer key becomes a one-file change.
- `docs/issue-anchored-plan.md` names `plan_grammar` as the normative plan-format owner.

### Non-goals
- Marker-drift sites (`decompose.py`, `learn_from_bugs.py`, `design_router.py`); file follow-ups, do not fix here.
- No change to which plans parse; the union of accepted forms is preserved.
- `issue_wire` stays the marker owner; `plan_grammar` owns grammar only.

### Approach sketch
- New `plan_grammar.py` (package chosen in Step 2b by import direction) exports: heading regex (union: `^#{2,3}`, four headings, bracket form), trailer key registry plus parsers, trailer composer, section iterator.
- Repoint six sites: `design_step5c.py`, `design_step2b.py`, `implement/preflight.py`, `calibration/difficulty.py`, `agents/_drafter.py`, `design/plan_quality.py` (plus `_plan_quality_commands.py`).
- Preserve the strict trailer validation the size gates depend on (octal and duplicate rejection) per I-Gate-1; this is a move plus dedupe, not a semantic change.
- Use a frozen dataclass for the parsed trailer set (G-Py-1, G-Fix-1).
- Update `docs/issue-anchored-plan.md` to name the module.

### Surfaces in scope
- `python/larch/...` new `plan_grammar.py`
- `design_step5c.py`, `design_step2b.py`, `implement/preflight.py`, `calibration/difficulty.py`, `agents/_drafter.py`, `design/plan_quality.py`, `_plan_quality_commands.py`
- `docs/issue-anchored-plan.md`

### Open questions
- Module package location (`larch/design/` vs `larch/issue/`); resolve in Step 2b by import-direction inspection.
