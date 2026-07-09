## Proposed Design Outline

### Goals
- Add `python/larch/lint/lint_suppression_reason.py`: a new lint that fails on `# noqa:`, `# type: ignore`, `# pyright: ignore`, and `# pylint: disable=` comments without inline reasons.
- Seed `python/suppression-reason-baseline.json` with all existing violations (shrink-only, per G-Enf-2).
- Wire the lint into the `py-lint-checks-fast` loop, pre-commit, and CI; document it in `docs/linting.md`.

### Non-goals
- Fixing existing unreasoned suppressions (baseline grandfathers them).
- Scanning test files under `python/larch/tests/` or `python/tests/`.
- Supporting preceding-line reasons for file-level suppressions (same-line only in v1).

### Approach sketch
- Mirror `lint_shared_convention_regex.py` and `lint_em_dash_output.py` structure: `scan_file()` + `main()` using `lint_common.run_file_lint`.
- Four grammar checkers (one per suppression type): noqa needs ` - reason`, the others need `  # reason`.
- Baseline check: JSON array keyed by `(file, text, occurrence)`; `--write` regenerates it.
- Registration in `python/larch/cli.py` + `py-lint-checks-fast` Makefile loop + `.pre-commit-config.yaml` hook.
- Test file in `python/tests/lint/test_lint_suppression_reason.py`.

### Surfaces in scope
- `python/larch/lint/lint_suppression_reason.py` (new)
- `python/tests/lint/test_lint_suppression_reason.py` (new)
- `python/suppression-reason-baseline.json` (new)
- `python/larch/cli.py` (registration)
- `Makefile` (check name + targets)
- `.pre-commit-config.yaml` (new hook)
- `docs/linting.md` (new table row)

### Open questions
- None.
