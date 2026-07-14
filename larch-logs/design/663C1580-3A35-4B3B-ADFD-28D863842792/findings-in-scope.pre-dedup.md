### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/lint/test_lint_complexity_baseline.py (new migration tests)
- **Concern**: [G-Wire-2] Migration tests assert only the identity-to-metric projection, not preservation of optional metadata. Scenario: A mixed record containing source_issue, reason, or operator_override could lose those fields while all planned assertions still pass
- **Proposed resolution**: Add a migration fixture with every optional field and assert the migrated output preserves them exactly 1. **[correctness] Optional migration metadata lacks direct coverage.** This is a risk-bearing migration path. Test exact preservation of `source_issue`, `reason`, and `operator_override`.



### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_complexity_baseline.py:440-452
- **Concern**: `_run_write` regeneration guard needs a legacy-tolerant raw-record probe, not strict `load_baseline` success/failure. Scenario: Grandfather migration adds only required `added_at`/`history`, so checking optional metadata alone misses migrated files. Using strict `load_baseline` also treats a partially migrated mix as load failure and allows `--write`, clobbering extended rows. Treating any successful load as migrated blocks `--write` on an empty `[]` bootstrap file.
- **Proposed resolution**: Specify the guard reads raw JSON and refuses `--write` when any record has `added_at`, `history`, or optional extended keys; allow only legacy four-field records or an empty array. Add tests for migrated refusal, empty-array allowance, and partial-migration refusal.



