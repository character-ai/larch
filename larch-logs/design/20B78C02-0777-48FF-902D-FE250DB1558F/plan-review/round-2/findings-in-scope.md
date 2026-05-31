Verifying the cited locations in the codebase so the aggregated findings match the code.
Normalized aggregator output from the three reviewer inputs (two merged, one kept separate):

### FINDING_1: write-session-env.sh is not safe to source for shared emit_plugin_root_env
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Edge
- **Severity**: important
- **Concern**: The plan expects `implement-bootstrap.sh` to source `write-session-env.sh` and call a shared `emit_plugin_root_env`, but the script is execute-only today: top-level argument parsing runs on source with empty `OUTPUT` and exits 1 before any emit runs. `implement-bootstrap.sh` disables errexit globally, so a failed source on the resume path can be ignored and resume continues without `plugin-root.env` / `CLAUDE_PLUGIN_ROOT` for post–Step-0 work. Duplicating emit logic in bootstrap would avoid the source failure but breaks single-sourcing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Pragmatic: Refactor write-session-env.sh: define emit_plugin_root_env at top; wrap existing main body in if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then ...; fi (ship-pr.sh pattern); source from implement-bootstrap resume branch only for the helper
  - From Cursor-Edge: Define emit_plugin_root_env near the top; wrap existing writer logic in if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then ... fi; document source-only use in write-session-env.md

### FINDING_2: Resume-tail plugin-root emit lacks explicit failure handling under errexit-off bootstrap
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: If the plan adds `emit_plugin_root_env` in the resume branch (`implement-bootstrap.sh` ~563–586) without return-code handling, failures (e.g. `mktemp`/`mv`, unreadable tmpdir) can be dropped while errexit remains off file-wide. Bootstrap already captures `write-session-env.sh` failures elsewhere (~675–678), but an unhandled emit failure could leave legacy tmpdirs without `plugin-root.env` while post–Step-0 fences no longer have the pre-bootstrap awk fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Mirror write-session-env: _emit_rc=0; emit ... || _emit_rc=$?; on non-zero emit_kv STEP_FAILED plugin-root-env and exit 2; extend test-session-env-roundtrip resume case to assert bootstrap path or emit non-zero propagation

**Merge notes (for voters, not machine output):** Input FINDING_1 and FINDING_2 describe the same behavioral risk (source-unsafe `write-session-env.sh` + silent resume continuation). Input FINDING_3 is separate: it assumes the shared helper exists and targets rc propagation and tests on the resume branch, not the `BASH_SOURCE` guard itself.
