# Review Round 1

- Mode: `diff`
- 1 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_6: Cursor quota signals not available to complete-path gate
- **Reviewer(s)**: dyn-dyn-quota-gate
- **Severity**: major
- **Concern**: The new quota gate in `python/larch/implement/dispatch_step2.py` reads only `st.sidecar_log`, but the Cursor implement launcher does not populate that sidecar on a successful exit. In `launch_cursor_implement_main`, Cursor runs with `capture_stdout_only=True` and never passes `stderr_path=sidecar`; `_append_implement_failure_if_nonzero` also returns immediately on exit code 0, so quota text is not copied into the sidecar. Codex gets stderr capture plus `_mirror_codex_quota_from_events`, but Cursor gets neither. For `--coder cursor`, a quota-truncated run can still return `STATUS=complete` with partial coverage and reach commit/disposition handling, leaving the original failure mode in place for Cursor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-quota-gate: Mirror the Codex pattern for Cursor (capture stderr into the sidecar and/or mirror quota markers from the JSON transcript), and in `dispatch_step2.py` fall back to `st.transcript_path` the way `classify_launch_failure()` already does with `output_file`, e.g. `is_quota_failure(..., sidecar=st.sidecar_log) or is_quota_failure(..., sidecar=st.transcript_path)`.
