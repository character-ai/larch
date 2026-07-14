### FINDING_1: Optional migration metadata lacks coverage
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Concern**: Migration tests cover only identity and metric projection, so optional metadata such as `source_issue`, `reason`, or `operator_override` could be lost without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a migration fixture with every optional field and assert the migrated output preserves them exactly 1. **[correctness] Optional migration metadata lacks direct coverage.** This is a risk-bearing migration path. Test exact preservation of `source_issue`, `reason`, and `operator_override`.

### FINDING_2: Regeneration guard must tolerate legacy and partial records
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: `_run_write` needs a raw-record probe that refuses regeneration for migrated or partially migrated data while still allowing an empty-array bootstrap file. Strict `load_baseline` success/failure cannot distinguish these cases and may clobber extended rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Specify the guard reads raw JSON and refuses `--write` when any record has `added_at`, `history`, or optional extended keys; allow only legacy four-field records or an empty array. Add tests for migrated refusal, empty-array allowance, and partial-migration refusal.
