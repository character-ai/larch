## Proposed Design Outline

### Goals
- Extend `Record` TypedDict and runtime validators to the 9-field schema (4 existing required + 2 new required + 3 optional).
- Migrate all 1,135 `complexity-baseline.json` entries to `added_at: "legacy"`, `history: []`.
- Update `serialize_baseline` to emit fields in stable, canonical order.

### Non-goals
- No changes to the `--write` path or gate/repeat-bump logic (Piece 2).
- No complexity-threshold changes.
- No schema policy for other `*-baseline.json` files.

### Approach sketch
- Split `BASELINE_KEYS` into `BASELINE_REQUIRED_KEYS` (6) and `BASELINE_OPTIONAL_KEYS` (3); keep or deprecate the old constant.
- Add `NotRequired` fields to `Record` TypedDict so the writer (still 4-field) has no type errors.
- Update `_validate_record` to require the 6 required keys and allow the 3 optional keys; reject unknown keys.
- Update `serialize_baseline` to write fields in explicit order: `file`, `code`, `qualified_symbol`, `metric`, `added_at`, `history`, then optional keys.
- Apply migration inline in a one-shot script or Python helper that adds `added_at: "legacy"` and `history: []` to every record.

### Surfaces in scope
- `python/larch/lint/lint_complexity_baseline.py`
- `python/complexity-baseline.json`
- `python/tests/lint/test_lint_complexity_baseline.py`

### Open questions
- None.
