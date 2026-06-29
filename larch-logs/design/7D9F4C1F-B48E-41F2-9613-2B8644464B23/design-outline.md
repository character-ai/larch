## Proposed Design Outline

### Goals
- Compress all 14 over-cap skill `description:` values to ≤200 chars, keeping each trigger clause (S017 compliant).
- Add `lint-skill-description-length` (Python + pre-commit hook) to enforce the cap in CI.

### Non-goals
- `SKILL.md` body prose.
- `@`-import chain prose (sibling A2).
- Modifying the external `agent-lint` repo.

### Approach sketch
- Surgically reword 14 over-cap descriptions (8 public + 6 dev-only) in place; no body edits.
- New `python/larch/lint/lint_skill_description_length.py`: parse YAML frontmatter, extract description value, fail if `len > 200`.
- Register via `("lint", "skill-description-length")` in `python/larch/cli.py`.
- Wire as a `local` pre-commit hook (always_run, SKILL.md file pattern) in `.pre-commit-config.yaml`.
- Add `lint-skill-description-length` Makefile target + `test-lint-skill-description-length` test target.
- Pytest module `python/test_lint_skill_description_length.py` covering pass, over-cap, missing-field, unquoted-value edge cases.

### Surfaces in scope
- `skills/*/SKILL.md` (8 descriptions to rewrite)
- `.claude/skills/*/SKILL.md` (6 descriptions to rewrite)
- `python/larch/lint/lint_skill_description_length.py` (new)
- `python/test_lint_skill_description_length.py` (new)
- `python/larch/cli.py` (register lint verb)
- `.pre-commit-config.yaml` (new hook entry)
- `Makefile` (new lint + test targets)

### Open questions
- None.
