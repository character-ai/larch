### OOS_1:
- **Description**: Plan omits registering test-design-step6.sh in the SKILL.md wrapper contract inventory beside test-design-step5c.sh. Scenario: Peer harness test-design-step5c.sh is pinned there; agent-lint orphaned-skill-files / S030 may flag a new unreferenced skills/design/scripts/test-*.sh during make lint even though Testing strategy requires a clean relevant-checks run
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:187-197
- **Phase**: design

