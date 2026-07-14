## Final Design Plan

## Plan

Adopt the approved nine-field schema while keeping Piece 2’s metadata-stamping and gate behavior out of scope. Committed baselines load only in the extended schema. The one-time migration adds grandfather metadata. Until Piece 2 can preserve metadata during regeneration, `--write` refuses to overwrite any extended or partially migrated baseline.

### UPDATED: python/larch/lint/lint_complexity_baseline.py

- Extend `Record` with `added_at`, `history`, `source_issue`, `reason`, and `operator_override`, using typed nested history and override records.
- Keep the new fields `NotRequired` in the live-record type so the unchanged four-field writer remains type-valid; require `added_at` and `history` at runtime when loading committed baselines.
- Replace `BASELINE_KEYS` with explicit required and optional key sets.
- Make strict baseline loading require all six committed fields, reject old four-field records, and reject unknown fields.
- Validate:
  - `added_at` as a non-empty string.
  - `history` as a list of exact `{date, metric}` records, with non-empty date strings and non-negative integer metrics.
  - `source_issue` as a positive integer when present.
  - `reason` as a non-empty string when present.
  - `operator_override` as an exact `{reason, issue}` record with a non-empty reason and positive integer issue.
  - Booleans are rejected for integer fields.
- Return validated optional metadata from `load_baseline`; do not reconstruct records in a way that drops it.
- Make `serialize_baseline` use canonical field order: `file`, `code`, `qualified_symbol`, `metric`, `added_at`, `history`, `source_issue`, `reason`, `operator_override`; omit absent optional fields, retain identity sorting, two-space indentation, and the trailing newline.
- Add `migrate_baseline(path: Path) -> int` that reads the raw legacy or partially migrated schema, rejects unknown fields or missing identity fields, adds only missing `added_at: "legacy"` and `history: []`, preserves optional metadata, verifies the `(file, code, qualified_symbol) -> metric` projection is unchanged, then writes through `serialize_baseline`.
- Add `--migrate` to `_parse_args`; it runs the migration instead of check or write and reports the migrated-record count.
- Add a fail-closed `_run_write` pre-write guard that inspects raw JSON before invoking the unchanged writer:
  - allow an empty-array bootstrap baseline or records containing only the legacy four keys;
  - refuse with exit 2, without modifying the file, when any record contains `added_at`, `history`, `source_issue`, `reason`, or `operator_override`, including partially migrated records that strict loading would reject;
  - print that baseline regeneration is disabled until Piece 2’s metadata-preserving writer lands.
- Keep four-field writer output, thresholds, and repeat-bump policy unchanged. Do not add metadata merge, stamping, history updates, or gate logic in this piece.

### UPDATED: python/complexity-baseline.json

- Generate with `python3 python/cli.py lint complexity-baseline --migrate`.
- Add `added_at: "legacy"` and `history: []` to all 1,136 records.
- Preserve every identity, metric, and sorted-record position.
- Serialize fields in the updated canonical order.

### UPDATED: python/tests/lint/test_lint_complexity_baseline.py

- Update strict-load fixtures to include required migration metadata.
- Test loading all required and optional fields.
- Test rejection of old four-field records, missing required fields, unknown keys, invalid scalar types, malformed history entries, and malformed overrides.
- Add stable-serialization coverage using shuffled input keys and optional fields.
- Add direct migration tests using synthetic legacy and mixed fixtures:
  - run `migrate_baseline` or `--migrate`;
  - assert missing metadata becomes `added_at: "legacy"` and `history: []`;
  - assert the identity-to-metric projection is unchanged;
  - assert unknown fields fail closed.
- Keep a checked-in baseline migration round-trip test that confirms strict loading and byte-stable serialization.
- Keep greenfield writer tests pinned to four-field output.
- Replace the conflicting write-then-strict-check assumption with regression coverage that:
  - migrates writer-style legacy output before strict loading;
  - verifies `--write` allows an empty-array bootstrap baseline;
  - verifies `--write` refuses an existing migrated baseline with exit 2, leaves its bytes unchanged, and the unchanged baseline still passes strict lint; and
  - verifies `--write` also refuses a partially migrated baseline containing any extended key, even though strict loading rejects that fixture.

## Edge cases

- Empty `history` is valid for grandfathered entries; malformed elements are rejected.
- Optional fields remain absent rather than serializing as `null`.
- Partial nested optional objects and empty metadata strings fail validation.
- Date validation remains structural in this piece; ISO-8601 and repeat-bump date semantics belong to Piece 2.
- A partially migrated baseline fails strict loading until migration completes.
- The raw regeneration guard distinguishes legacy records and an empty bootstrap array from migrated or partial records, preventing the unchanged writer from clobbering metadata.

## Testing strategy

- Run `cd python && python3 -m pytest tests/lint/test_lint_complexity_baseline.py`.
- Run `python3 python/cli.py lint complexity-baseline`.
- Run changed-file Python lint and type checks.
- Run `make lint`.
- Inspect the baseline diff or compare identity/metric projections to confirm migration added only grandfather metadata.

difficulty: MODERATE
diff_added: 3710
diff_deleted: 1210
mechanical_churn: true
oversize_override: operator
diff_lines: 4920
