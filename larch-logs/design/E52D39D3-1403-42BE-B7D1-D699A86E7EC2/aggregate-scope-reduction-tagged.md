### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/agents.py:83-87
- **Concern**: [SCOPE-REDUCTION] `_clone_path_from_parent_walk` from `cwd` cannot reach `.larch-keepalive` in the reported failure mode. Scenario: When `run_legacy_script` sets CWD to the plugin-cache root, keepalive lives under `$DESIGN_TMPDIR` (a separate session path), not in any ancestor of that CWD. Parent-walk adds code and an untested branch but does not recover the consumer repo for the bug scenario; tier 3 already depends on `DESIGN_TMPDIR`/`SESSION_TMPDIR` env
- **Proposed resolution**: Drop `_clone_path_from_parent_walk` and the parent-walk tier. Keep tier 3 env-based keepalive reads only
