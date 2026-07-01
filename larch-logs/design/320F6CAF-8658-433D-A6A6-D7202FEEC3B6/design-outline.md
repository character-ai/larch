## Proposed Design Outline

### Goals
- Relocate three flat lint tests to `python/tests/lint/` and update Makefile targets.
- Add a Python lint (`larch.lint.lint_flat_tests`) that fails on new flat `python/test_*.py`, with `test_support.py` in the explicit exemption list.
- Keep `make py-test` and CI harness green from new test locations.

### Non-goals
- Moving `test_support.py`; it stays flat with a lint exemption.
- Shard-assignment updates (the three tests have no existing shard entries).
- Any behavior change to the tested lints.

### Approach sketch
- Move the three files: `python/test_lint_tier1a.py`, `python/test_lint_bg_wait_coverage.py`, `python/test_lint_skill_description_length.py` → `python/tests/lint/`.
- Update three Makefile harness targets to use the new paths.
- Add `python/larch/lint/lint_flat_tests.py`: scans `python/test_*.py` at root, enforces exemption list, returns exit code 1 on violation.
- Register `python3 python/cli.py lint flat-tests` entry in `python/cli.py`.
- Add `python/tests/lint/test_lint_flat_tests.py` unit tests.
- Add a Makefile `test-lint-flat-tests` harness target.

### Surfaces in scope
- `python/test_lint_tier1a.py`, `python/test_lint_bg_wait_coverage.py`, `python/test_lint_skill_description_length.py` (moved)
- `python/tests/lint/` (destination for all three)
- `python/larch/lint/lint_flat_tests.py` (new lint module)
- `python/tests/lint/test_lint_flat_tests.py` (new test)
- `python/cli.py` (register new CLI verb)
- `Makefile` (update 3 harness targets + add new target)

### Open questions
- None.
