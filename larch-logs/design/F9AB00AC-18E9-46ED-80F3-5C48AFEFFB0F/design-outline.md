## Proposed Design Outline

### Goals
- Strengthen the consequence statement in `skills/design/SKILL.md` Step 3 so the polling prohibition names the cost (dangling task handle + blocked session exit)
- Add an explicit `run_in_background` sleep-loop polling NEVER rule to `skills/shared/orchestrator-never.md`
- Add a CI pin so neither literal can be silently removed

### Non-goals
- No runtime/script behavior changes
- Not adding new gates, retries, or fail-safes for the polling scenario
- Not modifying AGENTS.md (the root prohibition already exists there)

### Approach sketch
- Edit 2 occurrences in `skills/design/SKILL.md` Step 3 (initial fence + resume fence): replace bare "Wait for `<task-notification>`" with full consequence statement
- Add item #4 to `skills/shared/orchestrator-never.md` with the canonical NEVER/Why/How/CI-backed format
- Extend `scripts/test-implement-anti-polling-rule.sh` to pin both new literals
- Update sibling `scripts/test-implement-anti-polling-rule.md`

### Surfaces in scope
- `skills/design/SKILL.md` (2 line edits in Step 3)
- `skills/shared/orchestrator-never.md` (append 1 new item)
- `scripts/test-implement-anti-polling-rule.sh` (add 2 check calls)
- `scripts/test-implement-anti-polling-rule.md` (update coverage description)

### Open questions
- None.
