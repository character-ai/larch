## Proposed Design Outline

### Goals
- Remove both self-disarm channels from `_size_trigger_assessment` so no model-declared meta field suppresses the hard size trigger.
- OR-combine `diff_added` and `diff_lines` as independent signals; both always evaluated.
- Demote `mechanical_churn` to a presentation softener: it sets `soft` but never blocks `reasons.append`.
- Add a regression fixture pinning that #6524's exact meta trips the oversize path.

### Non-goals
- Changing `oversize_override: operator` semantics; operator-written override stays valid.
- Altering thresholds (`PLAN_SIZE_MAX_DIFF_ADDED`, `PLAN_SIZE_MAX_DIFF_LINES`, etc.).
- Touching firm_headings / surfaces checks added by #6527 (they are independent `if` branches).
- Updating any non-docs, non-test, non-plan-quality surfaces.

### Approach sketch
- In `python/larch/design/plan_quality.py`, rewrite `_size_trigger_assessment` lines 465-473: compute `size_diff_added` and `size_diff_lines` independently; `size_diff_raw = size_diff_added or size_diff_lines`; append both applicable basis keys unconditionally; set `soft` when `mechanical_churn == "true" and size_diff_raw` without suppressing the trigger.
- Update `TRIGGER_REASONS` and `SOFT_ADVISORY` emission to match: `soft=True` only affects prompt copy, never suppresses the trigger.
- Update `docs/issue-anchored-plan.md` to clarify OR-combination and that `mechanical_churn` only softens presentation.
- Add regression test `test_check_plan_size_6524_meta_trips_oversize` in `python/tests/design/test_plan_quality.py`.

### Surfaces in scope
- `python/larch/design/plan_quality.py`
- `python/tests/design/test_plan_quality.py`
- `docs/issue-anchored-plan.md`

### Open questions
- None.
