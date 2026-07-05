## Proposed Design Outline

### Goals
- Remove the em-dash from the MANDATORY readability directive constant so the rule doesn't contradict itself.
- Update the preamble lint regex to reject the em-dash form and add a test that it does.
- Add a new lint (`lint-em-dash-emitted`) that catches em-dashes in Python print/f-string literals and skill-markdown status-print lines, wired into Makefile and CI.

### Non-goals
- Scrubbing existing em-dashes from Python runtime output strings (prerequisite scrub issues handle that).
- Scanning arbitrary Markdown prose, external reviewer outputs, or the `larch-logs/` tree.
- Enforcing no-em-dash in docstrings, comments, or string literals that are not emitted output.

### Approach sketch
- Bulk find-and-replace: change `MANDATORY — READ ENTIRE FILE` to `MANDATORY: READ ENTIRE FILE` in ~86 files across `skills/`, `agents/`, `.claude/skills/`, Python source, and Python test fixtures.
- Update `MANDATORY_DIRECTIVE_RE` in `lint_readability_preamble.py` from `MANDATORY\s+[—-]\s+READ` to `MANDATORY:\s+READ`; update matching test constants and add a rejection test.
- New module `python/larch/lint/lint_em_dash_emitted.py`: tokenize-based scan of `.py` files under `python/larch/` for `—` in STRING tokens; scan `Print:` and `⏩`-prefixed lines in `skills/**/*.md` and `agents/**/*.md`. Pragma `# lint-em-dash-emitted: ok` to exempt intentional uses.
- Register verb `lint em-dash-emitted` in `larch/cli.py`, add Makefile target, pre-commit hook, and CI wiring (SKIP list in main lint job, runs in lint-local).

### Surfaces in scope
- `python/larch/core/alias_skill.py` (constant definitions)
- `python/larch/lint/lint_readability_preamble.py` (regex)
- `python/larch/lint/lint_em_dash_emitted.py` (new)
- `python/larch/cli.py` (verb registration)
- All `skills/**/*.md`, `agents/**/*.md`, `.claude/skills/**/*.md` with MANDATORY directive (86 files)
- `python/tests/core/test_alias_skill.py`, `python/tests/lint/test_lint_readability_preamble.py`, `python/tests/lint/test_lint_skill_closure_growth.py` (fixture updates)
- `python/tests/lint/test_lint_em_dash_emitted.py` (new)
- `Makefile`, `.pre-commit-config.yaml`, `.github/workflows/ci.yaml`

### Open questions
- None.
