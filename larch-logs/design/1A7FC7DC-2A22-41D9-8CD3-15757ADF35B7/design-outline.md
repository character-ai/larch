## Proposed Design Outline

### Goals
- Trim `/design` NEVER #4 and `/implement` NEVER #8 Monitor+recovery portion to ~40-word stubs.
- Keep the detailed premature-notification / background-waiter procedure exclusively in the shared docs that are already loaded on recovery turns.
- Update CI harness tokens in lockstep so no assertions break.

### Non-goals
- Changing the actual recovery contract or behavior.
- Editing `orchestrator-never.md` or `design-background-wait.md` content.
- Touching any other NEVER entries, other SKILL.md sections, or Python code.

### Approach sketch
- Replace `/design` NEVER #4 body with a ~40-word stub: Monitor ban, background-waiter ban, rely on `<task-notification>`, one foreground sentinel-probe per recovery turn, reference `design-background-wait.md` for the full procedure.
- Replace the Monitor+recovery portion of `/implement` NEVER #8 with a ~40-word stub: Monitor ban, background-waiter ban, notification-driven recovery, implement-vs-design asymmetry note, reference `orchestrator-never.md` NEVER #3 for the full procedure.
- Update `scripts/test-implement-anti-polling-rule.sh`: remove assertions that pinned tokens now removed from SKILL.md; add assertion that each stub references its shared doc.
- Update the `.md` sibling to match.

### Surfaces in scope
- `skills/design/SKILL.md` (Anti-patterns NEVER #4 only)
- `skills/implement/SKILL.md` (NEVER #8 Monitor+recovery portion only)
- `scripts/test-implement-anti-polling-rule.sh`
- `scripts/test-implement-anti-polling-rule.md`

### Open questions
- None.
