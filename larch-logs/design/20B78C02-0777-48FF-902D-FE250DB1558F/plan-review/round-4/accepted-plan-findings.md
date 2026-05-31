### FINDING_1: Sourcing `write-session-env.sh` must not enable errexit in `implement-bootstrap`
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge
- **Severity**: important
- **Concern**: `implement-bootstrap.sh` runs with `set -uo pipefail` (no errexit) so Step 0 can treat helper failures as best-effort. A proposed resume path that sources `write-session-env.sh` would run its top-level `set -euo pipefail` (line 32 today), lib-quiet init, argument parsing, and validation in the bootstrap shell. That leaks errexit into bootstrap and can abort resume on benign failures (e.g. missing `--output` on the sourced path, or any command that fails under `-e`). The `BASH_SOURCE` guard must be scoped so nothing outside it leaves `-e` or `exit` active in the parent shell.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define emit_plugin_root_env before the guard; move set -euo pipefail lib-quiet init and argument parsing inside if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; or run . write-session-env.sh and emit_plugin_root_env in a subshell so errexit does not leak
  - From Cursor-Edge: Keep set -euo pipefail lib-quiet init argument parsing validation and main write inside the BASH_SOURCE guard; only emit_plugin_root_env outside


### FINDING_2: `emit_plugin_root_env` needs a sourced return contract, not `exit`
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: When `emit_plugin_root_env` is invoked from a sourced bootstrap during `--resume-plan-tail`, using `exit` on skip or invalid values terminates the entire bootstrap script instead of returning control to the caller. Only the argv0 execution path should use `exit`; the sourced path must use `return`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Use return 0 on skip/invalid value; reserve exit for argv0 execution path only


