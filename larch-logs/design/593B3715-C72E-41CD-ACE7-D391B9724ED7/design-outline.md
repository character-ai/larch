## Proposed Design Outline

### Goals
- Append a new `## Migration discipline` section with `G-Mig-1` to `ARCHITECTURAL_GUIDELINES.md`.
- Place the section immediately before `## Enforcement philosophy`.
- Match content byte-for-byte with the issue-specified block.

### Non-goals
- No changes to any skill, script, or non-guideline file.
- No reformatting or editing of existing guideline entries.
- No changes to linting infrastructure.

### Approach sketch
- Read `ARCHITECTURAL_GUIDELINES.md` to confirm insertion point.
- Insert the `## Migration discipline` block verbatim before `## Enforcement philosophy`.
- Verify the file renders cleanly and existing entries are untouched.

### Surfaces in scope
- `ARCHITECTURAL_GUIDELINES.md` (insert-only)

### Open questions
- None.
