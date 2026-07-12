## Pieces

### Piece 1: Proposal contract — SKILL.md fields + guideline
- Scope: `skills/learn-from-bugs/SKILL.md` (add three required fields to sections 4, 5-lint/hook, 7 and filing body contracts; fail-closed completeness pass), `python/tests/skills/_structure_learn_from_bugs_specialized.py` (extend harness to pin three field names, both thresholds, fail-closed rule), `ARCHITECTURAL_GUIDELINES.md` (append G-Prev-1 under new Prevention discipline section)
- Firm-headings: skills/learn-from-bugs/SKILL.md, python/tests/skills/_structure_learn_from_bugs_specialized.py, ARCHITECTURAL_GUIDELINES.md
- Acceptance: `make test-learn-from-bugs-structure` passes; guideline present with correct ID and backing evidence
- Dependencies: none
- Size estimate: ~160 lines

### Piece 2: Lint-module-manifest enforcement machinery
- Scope: `python/larch/lint/lint_module_manifest.py` (new, on shared engine), `python/lint-module-manifest.json` (new, seeded legacy for all current lint_*.py), `python/tests/lint/test_lint_module_manifest.py` (new), `python/larch/cli.py` (register ("lint", "module-manifest")), `Makefile` (add targets + fast-lint set), `docs/linting.md` (document manifest contract)
- Firm-headings: python/lint-module-manifest.json, python/larch/lint/lint_module_manifest.py, python/tests/lint/test_lint_module_manifest.py, python/larch/cli.py, Makefile, docs/linting.md
- Acceptance: `make test-lint-module-manifest` passes; `make lint-module-manifest` exits clean; `make py-lint` and `make lint` stay green
- Dependencies: none
- Size estimate: ~535 lines
