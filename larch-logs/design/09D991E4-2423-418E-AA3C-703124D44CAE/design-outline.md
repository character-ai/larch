## Proposed Design Outline

### Goals
- Reduce context loaded on every default-mode Gate B entry by ~36 lines.
- Keep explicit-mode Gate B behavior unchanged; move it to a dedicated reference file.

### Non-goals
- No changes to Gate B logic, behavior, or test harness.
- No Python changes.
- No changes to `approval-gates.md` sections that serve both modes.

### Approach sketch
- Create `skills/design/references/approval-gates-explicit.md` with the two moved sections.
- In `approval-gates.md`: replace `### Prompt` and `### One-by-one iteration prompt` with a one-line pointer.
- In `SKILL.md` at Step 3.5: add a conditional load directive after the existing `approval-gates.md` read.

### Surfaces in scope
- `skills/design/references/approval-gates.md`
- `skills/design/references/approval-gates-explicit.md` (new)
- `skills/design/SKILL.md`

### Open questions
- None.
