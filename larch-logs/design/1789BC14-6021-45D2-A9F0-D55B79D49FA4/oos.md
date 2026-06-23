### OOS_1: Absorbed 1.r reference still keys entry off legacy `ROUTE` conditions
- **Description**: Absorbed 1.r reference still keys entry off legacy `ROUTE` conditions. Scenario: The plan retargets absorbed `1.r` orchestration in `SKILL.md` to `BOOTSTRAP_NEXT=rebase-routing`, but `rebase-checkpoint-routing.md` still says to load it when `ROUTE` is conflict, bail, missing, or malformed. That leaves a second entry contract outside the new directive lookup.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/references/rebase-checkpoint-routing.md:7-8
- **Phase**: design




Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted

### OOS_2: Absorbed 1.r entry guard still keys off ROUTE instead of BOOTSTRAP_NEXT
- **Description**: Absorbed 1.r entry guard still keys off ROUTE instead of BOOTSTRAP_NEXT. Scenario: The plan retargets SKILL.md absorbed 1.r entry to BOOTSTRAP_NEXT=rebase-routing (plan.txt:99-105) but does not update rebase-checkpoint-routing.md line 7 (load when ROUTE is conflict, bail, missing, or malformed). An orchestrator that treats the reference When-to-load line as authoritative may reintroduce a legacy Step 0 ROUTE gate alongside BOOTSTRAP_NEXT.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/references/rebase-checkpoint-routing.md:7
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

