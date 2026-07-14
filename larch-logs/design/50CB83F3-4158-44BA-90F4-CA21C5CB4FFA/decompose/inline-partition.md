## Pieces

### Piece 1: Lint core
- Scope: `python/larch/lint/lint_gh_argv_literal.py` (new lint module), `python/larch/cli.py` (CLI registration), `python/tests/lint/test_lint_gh_argv_literal.py` (tests). Implements the AST scan, pragma suppression, and `python3 python/cli.py lint gh-argv-literal` CLI entry point with full test coverage.
- Firm-headings: python/larch/lint/lint_gh_argv_literal.py, python/larch/cli.py, python/tests/lint/test_lint_gh_argv_literal.py
- Acceptance: `pytest python/tests/lint/test_lint_gh_argv_literal.py` passes; `python3 python/cli.py lint gh-argv-literal --root .` runs without error.
- Dependencies: none
- Size estimate: ~250 lines added

### Piece 2: CI wiring and docs
- Scope: `Makefile` (add `gh-argv-literal` to `py-lint-checks-fast`), `.pre-commit-config.yaml` (add `lint-gh-argv-literal` hook), `docs/linting.md` (add Linters table row).
- Firm-headings: Makefile, .pre-commit-config.yaml, docs/linting.md
- Acceptance: `make py-lint-checks-fast` runs the new lint; `pre-commit run lint-gh-argv-literal --all-files` succeeds; `docs/linting.md` has the new row.
- Dependencies: blocked-by Piece 1
- Size estimate: ~30 lines changed
