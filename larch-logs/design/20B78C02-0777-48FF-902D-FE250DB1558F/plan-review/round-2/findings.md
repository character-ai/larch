### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/write-session-env.sh:183-191 scripts/implement-bootstrap.sh:563-586
- **Concern**: Plan calls emit_plugin_root_env from implement-bootstrap but write-session-env.sh is execute-only today with no functions or BASH_SOURCE guard. Scenario: Sourcing the script as-is runs argument parsing with empty OUTPUT and exits 1 before emit runs; duplicating emit in bootstrap breaks single-sourcing
- **Proposed resolution**: Refactor write-session-env.sh: define emit_plugin_root_env at top; wrap existing main body in if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then ...; fi (ship-pr.sh pattern); source from implement-bootstrap resume branch only for the helper

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/write-session-env.sh:1-191
- **Concern**: Shared emit_plugin_root_env has no source-safe entry guard. Scenario: Plan has bootstrap source write-session-env.sh to call emit_plugin_root_env, but the script is top-level (no BASH_SOURCE guard). Sourcing runs arg validation and exits 1; implement-bootstrap.sh has errexit off (implement-bootstrap.sh:4-8), so resume can continue without plugin-root.env and post-Step-0 blocks lose CLAUDE_PLUGIN_ROOT
- **Proposed resolution**: Define emit_plugin_root_env near the top; wrap existing writer logic in if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then ... fi; document source-only use in write-session-env.md

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/implement-bootstrap.sh:563-586
- **Concern**: Resume-tail emit has no failure handling under errexit-off bootstrap. Scenario: Plan adds emit_plugin_root_env in the resume branch but not rc handling. Bootstrap captures write-session-env.sh failures (675-678) but errexit is disabled globally; an emit failure (mktemp/mv, unreadable tmpdir) can be ignored, leaving legacy tmpdirs without plugin-root.env while pre-bootstrap awk fallback is gone from post-Step-0 fences
- **Proposed resolution**: Mirror write-session-env: _emit_rc=0; emit ... || _emit_rc=$?; on non-zero emit_kv STEP_FAILED plugin-root-env and exit 2; extend test-session-env-roundtrip resume case to assert bootstrap path or emit non-zero propagation
