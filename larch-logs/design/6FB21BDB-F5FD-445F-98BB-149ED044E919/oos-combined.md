### OOS_1:
- **Description**: [OUT_OF_SCOPE] `/implement` NEVER #8 and `skills/shared/orchestrator-never.md` still describe only the background `until …; do sleep N; done` recovery waiter; this plan touches design recovery only.. Scenario: If `/implement` long-running fences hit the same premature-notification + killed-waiter pattern, operators get no sanctioned foreground sentinel probe there and may repeat the same costly `ps` polling workaround.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:240-249
- **Phase**: design
