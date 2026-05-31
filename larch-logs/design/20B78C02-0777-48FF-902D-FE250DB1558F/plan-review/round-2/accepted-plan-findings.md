### FINDING_1: write-session-env.sh is not safe to source for shared emit_plugin_root_env
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Edge
- **Severity**: important
- **Concern**: The plan expects `implement-bootstrap.sh` to source `write-session-env.sh` and call a shared `emit_plugin_root_env`, but the script is execute-only today: top-level argument parsing runs on source with empty `OUTPUT` and exits 1 before any emit runs. `implement-bootstrap.sh` disables errexit globally, so a failed source on the resume path can be ignored and resume continues without `plugin-root.env` / `CLAUDE_PLUGIN_ROOT` for post–Step-0 work. Duplicating emit logic in bootstrap would avoid the source failure but breaks single-sourcing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Pragmatic: Refactor write-session-env.sh: define emit_plugin_root_env at top; wrap existing main body in if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then ...; fi (ship-pr.sh pattern); source from implement-bootstrap resume branch only for the helper
  - From Cursor-Edge: Define emit_plugin_root_env near the top; wrap existing writer logic in if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then ... fi; document source-only use in write-session-env.md


