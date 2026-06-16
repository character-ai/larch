### FINDING_3:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/stall_recovery.py:1079-1083
- **Concern**: [SCOPE-REDUCTION] Terminal stall seeder change conflicts with the non-goal. Scenario: The approach says to keep stall-recovery seed-terminal-state unchanged, but also says to make the terminal stall path fail closed on a non-empty ship-pr-state.sh. Current terminal recovery rewrites STALL_TRACKING, STALL_STEP, and PHASE into an existing driver state; removing that rewrite can break existing transient-to-stall recovery.
- **Proposed resolution**: Remove the terminal-stall fail-closed bullet. Limit create-if-absent semantics to the new initial ship-pr-state seeder.
