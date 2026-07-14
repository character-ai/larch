## Decision 1: load_baseline backward compatibility
- **Question**: Should `load_baseline` accept both old 4-field records and new 6-field records, or require new-style only?
- **Resolution**: Require new-style only. The migration converts all 1,135 entries; `load_baseline` enforces the new schema. Old-style records fail validation. Tests using 4-field records need updating.
- **Source**: codebase (issue body: "Update `load_baseline` to handle the new schema"; acceptance: "migration round-trip test passes")

## Decision 2: TypedDict vs writer constraint
- **Question**: Making `added_at` and `history` required in `Record` would cause type errors in the writer (which still produces 4-field records). How to handle this?
- **Resolution**: Use `NotRequired` (or a separate `TypedDict` subclass) for new fields so the writer has no type errors. Runtime validation in `_validate_record` enforces them as required for loaded baseline records. The writer updates come in Piece 2.
- **Source**: codebase (writer path produces `Record` without new fields; issue: "The writer and gate logic are not changed in this piece")

## Decision 3: BASELINE_KEYS split for optional fields
- **Question**: `BASELINE_KEYS` currently used for strict key equality. With optional fields, how to validate?
- **Resolution**: Rename/replace with two sets: required keys (file, code, qualified_symbol, metric, added_at, history) and allowed-optional keys (source_issue, reason, operator_override). `_validate_record` checks all required keys present + no unknown keys. Implementation decision; no user input needed.
- **Source**: codebase
