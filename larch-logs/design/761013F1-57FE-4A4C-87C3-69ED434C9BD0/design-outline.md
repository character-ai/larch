## Proposed Design Outline

### Goals
- Add `lint_renderer_golden_tests`: fail on new uncovered `_render_*`/`*_rows` functions in `python/larch/report/`, warn on baselined ones.
- Add `lint_guidelines_note_wrapper_bypass`: hard-ban direct `_invalidate_guidelines_note(` calls outside `ship_guidelines.py`.
- Both lints run under the existing `make py-lint` sweep with no new CI job.

### Non-goals
- Do not add or modify existing tests in `python/tests/report/`.
- Do not enforce fixture quality (hostile widths, fallback shapes); that stays under G-Obs-5 review.
- Do not modify any report renderer or `ship_guidelines.py`.

### Approach sketch
- Add one module per lint in `python/larch/lint/`, following `lint_lifecycle_prefix_literal.py` structure.
- Lint 1: AST-scan top-level functions in `python/larch/report/*.py`; text-search `python/tests/report/*.py` for each name; compare against a JSON baseline (`renderer-golden-tests-baseline.json`); `--write` seeds/regenerates.
- Lint 2: text-scan (or AST-scan) `python/larch/**/*.py` (excluding `ship_guidelines.py` and test files) for `_invalidate_guidelines_note(`; zero-entry baseline; hard fail on any hit.
- Register both in `python/larch/cli.py` dispatch table and add to the Makefile sweep loop and regen targets.
- Seed Lint 1 baseline from the current tree (12 untested functions).

### Surfaces in scope
- `python/larch/lint/lint_renderer_golden_tests.py` (new)
- `python/larch/lint/lint_guidelines_note_wrapper_bypass.py` (new)
- `python/tests/lint/test_lint_renderer_golden_tests.py` (new)
- `python/tests/lint/test_lint_guidelines_note_wrapper_bypass.py` (new)
- `python/larch/cli.py` (register two new lint entries)
- `Makefile` (add two lints to sweep loop, add regen targets)
- `python/renderer-golden-tests-baseline.json` (new, seeded)

### Open questions
- None.
