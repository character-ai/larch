## Proposed Design Outline

### Goals
- Add PLR0911 guidance to the lint-fix-loop prompt so coders know to consolidate guards that return the same value.
- Add a PLR0911 preventive note to the implementer-base agent so Codex/Cursor avoid the violation upfront.

### Non-goals
- Change PLR0911 ruff configuration (limit stays at 6).
- Add `# noqa` suppression guidance (semantic consolidation is the preferred fix).
- Fix or refactor existing functions that exceed PLR0911 (this fix is forward-looking only).

### Approach sketch
- Add a `## Ruff complexity` section to `_compose_prompt` in `python/larch/implement/checks.py` — mirrors the existing Pyright guidance section.
- Add a PLR0911 bullet to the harness-awareness checklist in `agents/_implementer-base.md`.
- Regenerate `agents/codex-implementer.md` and `agents/cursor-implementer.md` from the updated base.
- Add a `test_compose_prompt_includes_plr0911_guidance` test to `python/test_checks.py`.

### Surfaces in scope
- `python/larch/implement/checks.py` (reactive: lint-fix-loop prompt)
- `python/test_checks.py` (test coverage for the prompt change)
- `agents/_implementer-base.md` (preventive: implementer harness checklist)
- `agents/codex-implementer.md` (regenerated)
- `agents/cursor-implementer.md` (regenerated)

### Open questions
- None.
