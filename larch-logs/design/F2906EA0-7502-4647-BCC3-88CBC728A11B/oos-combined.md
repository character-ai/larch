### OOS_2:
- **Description**: [OUT_OF_SCOPE] Cursor keychain preflight and preread remain outside the startup mutex. Scenario: On Darwin with empty CURSOR_API_KEY, Cursor security find-generic-password calls can still overlap with a Codex startup holding the new shared lock; this is adjacent to but beyond the approved path-rename scope
- **Reviewer**: Codex-Generic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/agents.py:499-567,scripts/lib-cursor-auth.sh:47-73,scripts/lib-cursor-auth.sh:157-203
- **Phase**: design
