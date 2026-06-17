### [Plan Review] FINDING_1

### FINDING_1: Unguarded int() in `_prior_immediate_round_end_s` can crash live progress
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The planned `_prior_immediate_round_end_s` helper (fallback when `round-start-s` is absent) uses `max(int(cols[7]))` on v1 ledger rows without a `try/except`. A corrupt or partial row that matches skill and round_n can raise `ValueError` and break the live `p`/progress report on the new fallback path, where the old phase-start fallback returned a chart instead of failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In `_prior_immediate_round_end_s`, wrap `int(cols[7])` in `try/except ValueError` and skip bad rows, matching `_progress_vendor_rows` parsing style


### [Plan Review] FINDING_2

### FINDING_2: `_persist_round_start` lacks symlink no-follow guards on expanded call path
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan moves `_persist_round_start` from escalation-only to every normal Step 5 round start. The current implementation uses `mkdir` and `_write_text` without symlink checks. A precreated `round-N` directory symlink or dangling `round-start-s` symlink under `IMPLEMENT_TMPDIR` could redirect the timestamp write outside the tmpdir before review starts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Mirror the design helper's no-follow write-once guards in `_persist_round_start`: skip symlinked round dirs and symlinked `round-start-s` paths, create only regular round dirs, and write only when the target is absent as a non-symlink

