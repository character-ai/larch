## Proposed Design Outline

### Goals
- Add three required proposal fields (Host, Size budget, Cheaper alternative) to learn-from-bugs lint/hook/test proposals.
- Add G-Prev-1 guideline to ARCHITECTURAL_GUIDELINES.md under a new Prevention discipline section.
- Add lint-module-manifest: JSON seed file, new lint module, CLI registration, Makefile targets, and docs entry.

### Non-goals
- No enforcement inside /design or /implement prompts.
- No retroactive re-justification of existing lint modules beyond seeded legacy entries.
- No changes to what /learn-from-bugs may propose; only what proposals must state.

### Approach sketch
- Extend SKILL.md Step 4 sections 4, 5 (lint/hook best-home), and 7 with three required fields; extend filing body contracts and completeness pass to treat missing fields as incomplete.
- Extend `_structure_learn_from_bugs_specialized.py` harness with pin checks for the three field names.
- Append G-Prev-1 under a new `## Prevention discipline` section at the end of ARCHITECTURAL_GUIDELINES.md.
- Create `python/larch/lint/lint_module_manifest.py` on the shared engine; create `python/lint-module-manifest.json` seeded with legacy entries for all current `lint_*.py` modules.
- Register `("lint", "module-manifest")` in `python/larch/cli.py`; add `lint-module-manifest` and `test-lint-module-manifest` Makefile targets; document in `docs/linting.md`.

### Surfaces in scope
- `skills/learn-from-bugs/SKILL.md`
- `python/tests/skills/_structure_learn_from_bugs_specialized.py`
- `ARCHITECTURAL_GUIDELINES.md`
- `python/larch/lint/lint_module_manifest.py` (new)
- `python/lint-module-manifest.json` (new)
- `python/larch/cli.py`
- `Makefile`
- `docs/linting.md`

### Open questions
- None.
