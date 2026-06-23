### OOS_1: Absorbed 1.r reference still keys entry off legacy `ROUTE` conditions
- **Description**: Absorbed 1.r reference still keys entry off legacy `ROUTE` conditions. Scenario: The plan retargets absorbed `1.r` orchestration in `SKILL.md` to `BOOTSTRAP_NEXT=rebase-routing`, but `rebase-checkpoint-routing.md` still says to load it when `ROUTE` is conflict, bail, missing, or malformed. That leaves a second entry contract outside the new directive lookup.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/references/rebase-checkpoint-routing.md:7-8
- **Phase**: design
