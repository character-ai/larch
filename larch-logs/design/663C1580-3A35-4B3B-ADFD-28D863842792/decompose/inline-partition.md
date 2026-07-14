## Pieces

### Piece 1: Schema update and tolerant validators
- Scope: Extend `Record` TypedDict with all 9 fields using `NotRequired`. Update `_validate_record` to allow but not require `added_at`/`history` (tolerate legacy 4-field records). Update `serialize_baseline` for stable field ordering. Update tests for new schema (no migration yet).
- Firm-headings: python/larch/lint/lint_complexity_baseline.py, python/tests/lint/test_lint_complexity_baseline.py
- Acceptance: `make lint` green; `python3 python/cli.py lint complexity-baseline` passes on unmigrated file; tests pass.
- Dependencies: none
- Size estimate: ~200 lines changed

### Piece 2: Baseline migration and strict validators
- Scope: Migrate `python/complexity-baseline.json` to add `added_at: "legacy"`, `history: []` to all 1,135 entries. Tighten `_validate_record` to require `added_at` and `history`. Update tests to require new schema.
- Firm-headings: python/complexity-baseline.json, python/larch/lint/lint_complexity_baseline.py, python/tests/lint/test_lint_complexity_baseline.py
- Acceptance: `make lint` green; migration round-trip test passes; no existing identities or metrics changed.
- Dependencies: blocked-by Piece 1
- Size estimate: ~4520 lines changed (mostly JSON migration)
