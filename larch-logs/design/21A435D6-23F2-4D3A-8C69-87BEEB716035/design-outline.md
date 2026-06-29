## Proposed Design Outline

### Goals
- Report always-loaded `.md` closure size (lines + estimated tokens) for `/design` and `/implement` separately, driven by `python/cli.py skill-closure report`.
- Lint (`python/cli.py lint skill-closure-growth`, wired into `make lint`) that fails a PR growing SKILL.md or its always-loaded closure past a committed baseline; bypass by updating the baseline.

### Non-goals
- Compressing or changing any runtime content.
- Recursing into referenced files (single level from SKILL.md only).
- Covering skills other than design and implement.
- External tokenizer dependency.

### Approach sketch
- New `python/larch/lint/lint_skill_closure.py`: closure parser (scan MANDATORY READ ENTIRE FILE directives; classify conditional vs unconditional by preceding If/When/only markers), line counter, token estimator (chars/4), and baseline compare.
- New `python/cli.py skill-closure report` verb: print per-file breakdown + totals.
- New `python/cli.py lint skill-closure-growth` verb: compare against `python/skill-closure-baseline.json`; `--write` regenerates baseline.
- New `lint-skill-closure-growth` Makefile target + pre-commit hook entry.
- Tests in `python/test_skill_closure.py`.
- Extend `larch-size` skill to show the closure summary via the report verb.

### Surfaces in scope
- `python/larch/lint/lint_skill_closure.py` (new)
- `python/test_skill_closure.py` (new)
- `python/skill-closure-baseline.json` (new, committed baseline)
- `python/cli.py` dispatch + any domain-registration module
- `Makefile`
- `.pre-commit-config.yaml`
- `.claude/skills/larch-size/scripts/larch_size.py`

### Open questions
- None.
