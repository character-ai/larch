## Pieces

### Piece 1: Writer, gate, and writer/gate tests
- Scope: Implement `--reason TEXT`, metadata-preserving writer merge, repeat-bump gate in check mode, and active-override listing in `lint_complexity_baseline.py`. Add writer/gate/override tests in `test_lint_complexity_baseline.py`. Update writer/gate section of `docs/linting.md`.
- Firm-headings: python/larch/lint/lint_complexity_baseline.py, python/tests/lint/test_lint_complexity_baseline.py
- Acceptance: `make lint` green; gate fails on second bump within 14 days; gate passes on first bump; override silences gate; writer preserves metadata; byte-stable rewrites pass.
- Dependencies: none
- Size estimate: ~420 diff lines

### Piece 2: Debt report, CLI registration, docs, and Makefile
- Scope: Add `lint_complexity_debt.py` with `--report` verb. Register `lint complexity-debt` in `cli.py`. Add debt-report tests in `test_lint_complexity_baseline.py`. Update `docs/linting.md` with debt-report section. Add `lint-complexity-debt` Makefile target. Update `regen-complexity-baseline` Makefile comment.
- Firm-headings: python/larch/lint/lint_complexity_debt.py, python/larch/cli.py, python/tests/lint/test_lint_complexity_baseline.py, docs/linting.md, Makefile
- Acceptance: `make lint` and `make py-lint` green; debt report prints all sections; `make lint-complexity-debt` runs successfully.
- Dependencies: none
- Size estimate: ~300 diff lines
