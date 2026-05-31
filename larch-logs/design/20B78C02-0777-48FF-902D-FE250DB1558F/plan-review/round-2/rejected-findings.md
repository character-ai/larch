### [Plan Review] FINDING_2

### FINDING_2: Resume-tail plugin-root emit lacks explicit failure handling under errexit-off bootstrap
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: If the plan adds `emit_plugin_root_env` in the resume branch (`implement-bootstrap.sh` ~563–586) without return-code handling, failures (e.g. `mktemp`/`mv`, unreadable tmpdir) can be dropped while errexit remains off file-wide. Bootstrap already captures `write-session-env.sh` failures elsewhere (~675–678), but an unhandled emit failure could leave legacy tmpdirs without `plugin-root.env` while post–Step-0 fences no longer have the pre-bootstrap awk fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Mirror write-session-env: _emit_rc=0; emit ... || _emit_rc=$?; on non-zero emit_kv STEP_FAILED plugin-root-env and exit 2; extend test-session-env-roundtrip resume case to assert bootstrap path or emit non-zero propagation

**Merge notes (for voters, not machine output):** Input FINDING_1 and FINDING_2 describe the same behavioral risk (source-unsafe `write-session-env.sh` + silent resume continuation). Input FINDING_3 is separate: it assumes the shared helper exists and targets rc propagation and tests on the resume branch, not the `BASH_SOURCE` guard itself.

