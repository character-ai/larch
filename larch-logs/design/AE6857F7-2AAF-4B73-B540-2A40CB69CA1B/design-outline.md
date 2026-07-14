## Proposed Design Outline

### Goals
- Enforce engine-based lint banning `# pylint: skip-file` in `python/larch/` runtime modules.
- Ban blanket per-file `disable=R0801`/`disable=duplicate-code` at the module level in `python/larch/`.
- Burn down `_oos.py`'s skip-file by removing it and fixing the underlying R0801 violations.

### Non-goals
- Modifying `lint_suppression_reason.py` or its baseline (different scope and purpose).
- Banning skip-file outside `python/larch/`.
- Changing R0801 thresholds or refactoring `duplicate_code.py`.

### Approach sketch
- New `python/larch/lint/lint_pylint_skip_file.py` with one `LintRule` using `engine.py` `run_rule`.
- `detect` tokenizes each source file and reports `# pylint: skip-file` and file-level R0801 disables.
- Baseline `python/pylint-skip-file-baseline.json` grandfathers 16 current instances with reasons.
- Remove `# pylint: skip-file` from `_oos.py`; run `duplicate-code` lint to find violations; fix them.
- Wire into `larch/cli.py`, `Makefile` `py-lint-checks-fast` loop, and `.pre-commit-config.yaml`.

### Surfaces in scope
- `python/larch/lint/lint_pylint_skip_file.py` (new)
- `python/tests/lint/test_lint_pylint_skip_file.py` (new)
- `python/pylint-skip-file-baseline.json` (new)
- `python/larch/issue/_oos.py` (remove skip-file + R0801 fixes)
- `python/larch/cli.py` (add registration)
- `Makefile` (loop + regen target)
- `.pre-commit-config.yaml` (add hook)

### Open questions
- What specific R0801 violations exist in `_oos.py`? Discovered during implementation by running the duplicate-code lint after removing skip-file.
