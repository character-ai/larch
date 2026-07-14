### FINDING_2: Regeneration guard must tolerate legacy and partial records
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: `_run_write` needs a raw-record probe that refuses regeneration for migrated or partially migrated data while still allowing an empty-array bootstrap file. Strict `load_baseline` success/failure cannot distinguish these cases and may clobber extended rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Specify the guard reads raw JSON and refuses `--write` when any record has `added_at`, `history`, or optional extended keys; allow only legacy four-field records or an empty array. Add tests for migrated refusal, empty-array allowance, and partial-migration refusal.


