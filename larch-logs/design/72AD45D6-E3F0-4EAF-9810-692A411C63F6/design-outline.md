## Proposed Design Outline

### Goals
- Require full, append-ready wording for all proposal sections (4, 5, 6) in `learn-from-bugs` Step 4.
- Eliminate the "terse" instruction and compressed template from section 6.
- Add a readability carve-out: exactness takes precedence over brevity for proposal text.

### Non-goals
- No changes to sections 1, 2, 3, or 7 of the report template.
- No changes to Step 1, 2, 3, or 5 of the skill.
- No Python/Bash code changes; prose-only edit to SKILL.md.

### Approach sketch
- Edit `skills/learn-from-bugs/SKILL.md` Step 4 sections 4, 5, and 6 only.
- Section 5: add requirement for full normative statement per invariant; add `rule` sub-requirement for complete `.claude/rules/*.md` draft.
- Section 6: remove "terse" and the compressed one-line template; require full imperative sentence, full Why, full Deviate-when in complete sentences.
- Section 4: add requirement that each lint rule includes a complete statement of what it flags, on which surface, with suppression and baseline policy.
- Add an inline carve-out sentence in the proposal sections noting exactness overrides brevity.

### Surfaces in scope
- `skills/learn-from-bugs/SKILL.md` (Step 4 only: sections 4, 5, 6)

### Open questions
- None.
