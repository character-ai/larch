### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/status/SKILL.md:29
- **Concern**: Item 4 distinguishes one-down vs both-down but status.sh emits only DEGRADED and per-vendor presence KVs not BOTH_DOWN. Scenario: Status SKILL rewrite can still emit one generic degraded sentence and fail Item 4
- **Proposed resolution**: Add an explicit render rule: when DEGRADED=true and both CODEX_PRESENT and CURSOR_PRESENT are false describe both-down hard-fail; when exactly one is false describe one-down operator confirmation; do not assume BOTH_DOWN is available from status.sh

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-sessionstart-health.sh:56-67
- **Concern**: Item 5 collect-results regression does not pin how the stub records LARCH_TOKEN_SESSION_ID for assertion. Scenario: Implementer may assert parent-shell env or hook stdout and ship a test that never exercises line 192 child env
- **Proposed resolution**: Require the resolve-implement-tmpdir stub to write LARCH_TOKEN_SESSION_ID to a dedicated temp file and assert that file is empty while the harness pre-exports a stale token outside env -i
