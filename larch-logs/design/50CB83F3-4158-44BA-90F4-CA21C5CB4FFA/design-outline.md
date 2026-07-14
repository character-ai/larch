## Proposed Design Outline

### Goals
- Add a hard-ban lint: any `["gh", ...]` or `("gh", ...)` Python argv literal outside `python/larch/git/` fails CI.
- Suppress test fixtures via inline pragma (`# lint-gh-argv-literal: ok <reason>`).
- Wire the lint into `py-lint-checks-fast`, pre-commit, and `docs/linting.md`.

### Non-goals
- Remove or modify the existing `subprocess-via-runner` gh-baseline mechanism.
- Migrate any existing callers (those are blocked-by repoint issues).
- Scan non-Python files or Bash scripts (separate lint already covers `--body`/`--notes`).

### Approach sketch
- New module `python/larch/lint/lint_gh_argv_literal.py`: AST walk, flag `ast.List`/`ast.Tuple` with `"gh"` as first `ast.Constant` element.
- Exempt `python/larch/git/` entirely; apply standard test-file exemptions (test_*.py, conftest.py, test_support.py, review_test_support.py).
- Inline pragma token `lint-gh-argv-literal` for production-side exceptions.
- Register in `python/larch/cli.py`; add to `py-lint-checks-fast` loop in `Makefile`; add pre-commit hook in `.pre-commit-config.yaml`.
- Add row in `docs/linting.md` Linters table.
- Tests in `python/tests/lint/test_lint_gh_argv_literal.py`.

### Surfaces in scope
- `python/larch/lint/lint_gh_argv_literal.py` (new)
- `python/larch/cli.py` (lint command registration)
- `Makefile` (py-lint-checks-fast list)
- `.pre-commit-config.yaml` (new hook)
- `docs/linting.md` (new row)
- `python/tests/lint/test_lint_gh_argv_literal.py` (new)

### Open questions
- None.
