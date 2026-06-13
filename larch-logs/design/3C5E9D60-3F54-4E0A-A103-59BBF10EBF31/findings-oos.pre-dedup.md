### OOS_1:
- **Description**: [OUT_OF_SCOPE] Session wrapper sibling contract not updated after gate fold. Scenario: `design-step0-degraded.md` is deleted; session.md still describes only session setup with no degraded-gate invariants (STEP0_STATUS, sentinel writes, stdout filtering).
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step0-session.md:1-19
- **Phase**: design

### OOS_1:
- **Description**: [SCOPE-REDUCTION] Wrapper-side .degraded-tools-gate-prompted re-entry branch is new vs current degraded.sh. Scenario: Plan adds both-down+sentinel → degraded-both-down-auto inside session; design-step0-degraded.sh has no sentinel check (prompt-side guard only). Not required for the 6→3 Bash reduction; acceptance asks unchanged degraded semantics.
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step0-session.sh:42-43
- **Phase**: design

