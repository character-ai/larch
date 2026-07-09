## Proposed Design Outline

### Goals
- Add G-Root-1 to document the rule: resolve repo roots from run state, not ambient cwd.
- Cite the three verified evidence issues (#4490, #4509, #6049) so the guideline traces to concrete defects.
- Satisfy the acceptance criterion: `python3 python/cli.py architectural-guidelines read` includes G-Root-1.

### Non-goals
- No code refactoring to comply with the new guideline.
- No changes to ARCHITECTURAL_INVARIANTS.md.
- No new Python logic or test changes.

### Approach sketch
- Insert a new `## Execution roots` section in `ARCHITECTURAL_GUIDELINES.md` after `## CLI surface` and before `## Security`.
- Add `### G-Root-1: ...` as the sole entry in that section using the issue-proposed text.
- Verify that the ID matches `GUIDELINE_HEADING_RE` (`G-Root-1` passes the regex).
- Confirm `architectural-guidelines read` returns G-Root-1.

### Surfaces in scope
- `ARCHITECTURAL_GUIDELINES.md`

### Open questions
- None.
