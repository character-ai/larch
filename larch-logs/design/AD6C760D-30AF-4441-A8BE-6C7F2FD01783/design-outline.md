## Proposed Design Outline

### Goals
- Stop the orchestrator agent from asking users for confirmation before filing accepted OOS items via `/larch:issue`
- Apply the fix to both `/design` Step 5b and `/implement` bash-path Step 9a.1

### Non-goals
- Changing OOS acceptance criteria, pipeline logic, or which items get filed
- Modifying the `/implement` Python path (`python/cli.py oos file`), which is already fully automatic

### Approach sketch
- Add explicit "do NOT ask for confirmation" instruction to `finalize-step5.md` § NEXT_ACTION=file-issues
- Add same instruction to `oos-pipeline.md` step 4
- Reinforce in `skills/design/SKILL.md` Step 5b `file-issues` dispatch bullet

### Surfaces in scope
- `skills/design/references/finalize-step5.md`
- `skills/implement/references/oos-pipeline.md`
- `skills/design/SKILL.md`

### Open questions
- None.
