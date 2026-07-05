## Proposed Design Outline

### Goals
- Add the merit gate to the `combine-issues` SKILL.md frontmatter `description:` so operators discover it from the skill catalog.
- Update the `docs/skills.md` catalog blurb to reflect the merit gate.
- Add rescue-ambiguity handling to oos-4: zero-match defaults to keep-all; multi-match requires re-confirmation.

### Non-goals
- No changes to the Python CLI or any test files.
- No changes to the merit-gate logic itself (already implemented).
- No new CLI flags or schema changes.

### Approach sketch
- Edit the frontmatter `description:` in `.claude/skills/combine-issues/SKILL.md` (under the 200-char cap, preserving `Use when` trigger phrasing).
- Edit the catalog blurb in `docs/skills.md` at the combine-issues section.
- Expand the free-prose rescue bullet in oos-4 with zero-match (keep-all) and multi-match (re-confirm) clauses.

### Surfaces in scope
- `.claude/skills/combine-issues/SKILL.md` (frontmatter + oos-4 prose)
- `docs/skills.md` (catalog blurb at the combine-issues entry)

### Open questions
- None.
