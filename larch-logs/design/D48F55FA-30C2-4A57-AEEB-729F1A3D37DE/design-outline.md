## Proposed Design Outline

### Goals
- Reduce `/implement` Phase-3 conflict-resolution context by ~380 lines by having `conflict-resolution.md` load a smaller Code-Reviewer-only fragment instead of the full 652-line `reviewer-templates.md` catalog.
- Keep the split file automatically in sync with the canonical source via a new generator verb and CI drift check (same pattern as `agents/code-reviewer.md`).

### Non-goals
- Changing any other consumer of `reviewer-templates.md` (rendering.py `render reviewer`, `/design` plan review, `/review`, `/research`).
- Modifying the Code Reviewer archetype body in any way.
- Python migration; this is a file-split with a generator, not a md-to-py extraction.

### Approach sketch
- Add `_conflict_resolution_code_reviewer_text()` in `python/larch/rendering/rendering.py` that extracts the Variables section and the Code Reviewer archetype from `reviewer-templates.md` verbatim, prepends an AUTO-GENERATED header, and returns the composed text.
- Wire into `generate_conflict_resolution_code_reviewer_main()` + `_GENERATOR_VERB_TO_FUNC` dispatch dict + `AUTO_HEADER_BY_VERB`.
- Register in `scripts/generators.tsv`; CI `agent-sync` enforces drift going forward.
- Run the generator to produce the new file.
- Update `conflict-resolution.md` line 74 to reference the new file.
- Update `reviewer-templates.md` Update triggers and `.claude/rules/reviewer-archetype-generation.md`.
- Add new file to `BACKTICKED_FOCUS_FILES` in `voting.py`.

### Surfaces in scope
- `python/larch/rendering/rendering.py`
- `scripts/generators.tsv`
- `skills/shared/reviewer-templates-code-reviewer.md` (new, generated)
- `skills/implement/references/conflict-resolution.md`
- `skills/shared/reviewer-templates.md` (Update triggers only)
- `.claude/rules/reviewer-archetype-generation.md`
- `python/larch/review/voting.py` (BACKTICKED_FOCUS_FILES only)

### Open questions
- None.
