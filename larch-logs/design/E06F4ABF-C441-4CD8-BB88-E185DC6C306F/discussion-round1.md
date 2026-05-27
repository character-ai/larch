## Decision 1: Strictness of monitor_rc enforcement
- **Question**: How strict should the new monitor_rc enforcement be?
- **Resolution**: Minimal-presence (literal Suggested Fix). Assert three tokens: `monitor_rc=` init within 3 non-blank lines above monitor; `|| monitor_rc=` on monitor's logical-end line; any `if`/`case` referencing `monitor_rc` later in the fence. No structural two-branch shape verification.
- **Source**: user
