### [Plan Review] FINDING_2

### FINDING_2: RUN_ID lookup and ndjson path resolution are underspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The helper's RUN_ID/log-root lookup is not defined tightly enough. If RUN_ID is not recovered from tmpdir artifacts, the ndjson guard is skipped and duplicates can re-append after a flush.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "Resolve `run_id` from session artifacts when env is unset; resolve batch path to `implement_tmpdir / "larch-logs" / "implement" / run_id / "execution-issues.ndjson"`; exit 2 only for missing tmpdir, not missing run_id."
  - From Cursor-Innovation: "Resolve RUN_ID from parent-issue.md, session-env.sh, or LARCH_RUN_ID; read implement_tmpdir/larch-logs/implement/RUN_ID/execution-issues.ndjson; cover missing-RUN_ID skip and ndjson-hit duplicate in tests"
  - From Codex-Innovation: "Resolve the run id inside the helper from --run-id or from IMPLEMENT_TMPDIR artifacts such as parent-issue.md, session-id, or session-env.sh/LARCH_RUN_ID, and check $IMPLEMENT_TMPDIR/larch-logs/implement/$RUN_ID/execution-issues.ndjson before writing; keep skip behavior only when no run id can be recovered."
  - From Cursor-Pragmatic: "Resolve RUN_ID from $IMPLEMENT_TMPDIR/parent-issue.md with session-id fallback, matching execution_issues.refresh_execution_issues, before reading larch-logs/implement/$RUN_ID/execution-issues.ndjson."
  - From Codex-Requirements: "Add --run-id to the helper CLI and prompt call, default it from RUN_ID/LARCH_RUN_ID or ship-pr-state.sh, validate it, and check $IMPLEMENT_TMPDIR/larch-logs/implement/$RUN_ID/execution-issues.ndjson."


### [Plan Review] FINDING_3

### FINDING_3: Append-only helper does not prevent duplicate flush rows
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The proposed append-only fix does not address the documented duplicate mode in the flush renderer itself. Even if the helper dedups re-emissions, a second flush can still write duplicate rows into execution-issues.ndjson.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "Keep the helper for post-flush re-emission, but add a minimal flush-side fix in run_log_flush.py so _render_execution_issues_batch does not append rows whose structured_body_dedupe_keys are already in the batch, or document that acceptance criterion 2 remains unmet."


