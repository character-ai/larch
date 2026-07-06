### OOS_1: Shared orchestrator NEVER still documents default threshold 5 and UserPromptSubmit-only blocking
- **Description**: Shared orchestrator NEVER still documents default threshold 5 and UserPromptSubmit-only blocking. Scenario: The plan updates `design-background-wait.md` and `skills/design/SKILL.md` but not `orchestrator-never.md` NEVER #5, which agents load on recovery paths. Hooks will enforce threshold 3 and Stop direct-block, but stale shared authority can still teach the old contract.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/shared/orchestrator-never.md:13
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: Shared NEVER #5 still documents default threshold 5 and UserPromptSubmit-only blocking
- **Description**: Shared NEVER #5 still documents default threshold 5 and UserPromptSubmit-only blocking. Scenario: The plan updates `skills/shared/design-background-wait.md` and `skills/design/SKILL.md` but not `orchestrator-never.md`, which AGENTS.md and `test-implement-anti-polling-rule.sh` still treat as authority for bg-wait polling and breaker behavior. Agents that load NEVER #5 can keep expecting UserPromptSubmit blocking at K=5 after the hooks change.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/shared/orchestrator-never.md:13
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_3: Structure pins do not cover the new breaker or denied-Read contracts on shared NEVER
- **Description**: Structure pins do not cover the new breaker or denied-Read contracts on shared NEVER. Scenario: `test-design-structure.sh` will pin updated wording in design skill/shared wait docs but leaves `orchestrator-never.md` unpinned on threshold/event model, so a later doc drift on NEVER #5 would not fail CI even after this fix lands.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/test-design-structure.sh:196-277
- **Phase**: design

Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

