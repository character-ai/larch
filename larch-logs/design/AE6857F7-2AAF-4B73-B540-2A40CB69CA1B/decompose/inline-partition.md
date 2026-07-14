## Pieces

### Piece 1: contract-unification G1: Engine unsuppressible-rule mode
- Scope: Add `allow_inline_suppression: bool = True` field to `LintRule` in `engine.py`. When `False`, `_scan_source` skips the pragma check so rules that ban specific patterns cannot be bypassed by an inline pragma. Update `_validate_rule` and `_scan_source` to honor the new field. Add tests proving unsuppressible rules retain findings despite a matching reason-bearing pragma, and that ordinary rules still honor suppression.
- Firm-headings: python/larch/lint/engine.py, python/tests/lint/test_lint_engine.py
- Acceptance: `python3 -m pytest python/tests/lint/test_lint_engine.py -q` passes, covering the unsuppressible flag on and off.
- Dependencies: none
- Size estimate: ~60 lines

### Piece 2: contract-unification G2: Pylint skip-file ban rule and _oos.py burndown
- Scope: New `lint_pylint_skip_file.py` using `engine.py` unsuppressible `LintRule`. New `test_lint_pylint_skip_file.py`. New `python/pylint-skip-file-baseline.json` with 16 grandfathered entries. Remove `# pylint: skip-file` from `_oos.py` and fix resulting R0801 violations. Wire into `larch/cli.py`, `Makefile` `py-lint-checks-fast` loop and regen target, and `.pre-commit-config.yaml` hook.
- Firm-headings: python/larch/lint/lint_pylint_skip_file.py, python/tests/lint/test_lint_pylint_skip_file.py, python/pylint-skip-file-baseline.json, python/larch/issue/_oos.py, python/larch/cli.py, Makefile, .pre-commit-config.yaml
- Acceptance: `python3 -m pytest python/tests/lint/test_lint_pylint_skip_file.py -q` passes. `python3 python/cli.py lint pylint-skip-file` exits 0. `make py-lint-duplicate-code` passes with `_oos.py` included. `make py-lint-checks-fast` passes.
- Dependencies: blocked-by Piece 1
- Size estimate: ~440 lines
