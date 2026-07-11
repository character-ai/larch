### OOS_1: FORKED_TARGET precedence differs from scope_disposition plan
- **Description**: FORKED_TARGET precedence differs from scope_disposition plan. Scenario: stall_recovery reads ship-pr-state FORKED_TARGET or session-env with OR fallback when ship key is empty. scope_disposition will treat an existing ship-pr-state.sh as authoritative and ignore session-env even when FORKED_TARGET is absent, so forked detection can disagree across helpers in the same run.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/state/stall_recovery.py:96-97
- **Phase**: design



