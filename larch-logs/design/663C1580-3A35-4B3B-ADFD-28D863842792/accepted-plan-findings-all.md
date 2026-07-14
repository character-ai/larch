### FINDING_1: `--write` can invalidate migrated baselines
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: Strict loading requires metadata that the unchanged writer omits. Regeneration can erase migration metadata and produce a baseline that immediately fails lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In Piece 1 add a fail-closed --write guard (or minimal merge that preserves committed metadata) until Piece 2 owns writer stamping; document that regen-complexity-baseline is blocked until then
  - From Codex-Arch: P land metadata-aware writing atomically with strict loading, or defer strict validation until Piece 2; retain a write-then-check regression test.
  - From Cursor-Innovation: In _run_write, fail closed when baseline_path already exists and load_baseline would require extended rows (stderr: regen disabled until Piece 2 writer). Do not add metadata merge logic in Piece 1; that stays Piece 2.
  - From Codex-Innovation: Sequence Piece 2 before this change or land both atomically; otherwise add a transitional writer path and retain write-then-check coverage
  - From Cursor-Pragmatic: Add a fail-closed pre-write guard (not Piece-2 metadata merge): if baseline_path exists and any on-disk row already has extended schema or load_baseline would require added_at/history refuse --write with exit 2 and a clear message that regen stays disabled until Piece 2; keep four-field writer output for greenfield tests only
  - From Codex-Pragmatic: Make --write emit valid migrated records, or land strict loading with the writer changes; retain write-then-check coverage
  - From Cursor-Requirements: Until Piece 2 owns metadata-preserving rewrite, fail closed on --write when the on-disk baseline already requires added_at/history (or when any row has migration metadata); print stderr that regen is disabled until the writer piece lands
  - From Codex-Requirements: Make --write emit a valid migrated schema in this piece, or preserve legacy compatibility until Piece 2. Retain a write-then-check regression test.


### FINDING_4: Legacy migration is not directly tested [OUT_OF_SCOPE]
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-Schema Migration Auditor, Codex-dyn-Schema Migration Auditor
- **Severity**: minor
- **Concern**: Testing only the already-migrated file can miss broken migration wiring or altered identity/metric projections.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a unit test that writes a small four-field fixture, runs migrate_baseline (or main --migrate), asserts added_at legacy and empty history on every row, unchanged identity/metric projections, and rejection of unknown keys
  - From Cursor-dyn-Schema Migration Auditor: Add an explicit test that writes a synthetic legacy four-field baseline, runs migrate_baseline (or main --migrate), asserts every row gains added_at="legacy" and history=[], and compares before/after (file,code,qualified_symbol)→metric projections for equality
  - From Codex-dyn-Schema Migration Auditor: Run migration on legacy and mixed fixtures; assert complete metadata and exact identity/metric projection preservation


### FINDING_5: Strict date validation is deferred [OUT_OF_SCOPE]
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: Non-empty but malformed dates could later break repeat-bump date calculations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Strict ISO-8601 validation for history[].date can wait for Piece 2 gate logic; Piece 1 only needs structural validation of non-empty strings.


### FINDING_2: Regeneration guard must tolerate legacy and partial records
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: `_run_write` needs a raw-record probe that refuses regeneration for migrated or partially migrated data while still allowing an empty-array bootstrap file. Strict `load_baseline` success/failure cannot distinguish these cases and may clobber extended rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Specify the guard reads raw JSON and refuses `--write` when any record has `added_at`, `history`, or optional extended keys; allow only legacy four-field records or an empty array. Add tests for migrated refusal, empty-array allowance, and partial-migration refusal.


