### OOS_1:
- **Description**: Shared NEVER #3 still lists Monitor waits and backgrounded watcher loops with no premature-notification recovery carve-out. Scenario: /implement NEVER #8 ends with "See orchestrator-never.md" before the new recovery text; agents that treat the shared file as the complete contract may still avoid the sanctioned single until-waiter recovery or read the recovery exception as conflicting with NEVER #4
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/orchestrator-never.md:9-11
- **Phase**: design

