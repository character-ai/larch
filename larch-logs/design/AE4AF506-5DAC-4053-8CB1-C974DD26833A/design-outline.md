## Proposed Design Outline

### Goals
- Add `lint_lifecycle_prefix_literal.py` to flag hand-written lifecycle/bug prefix literals in comparison and match positions.
- Wire the lint into `py-lint-checks-fast`, cli.py, and the Makefile regen target.
- Seed a reason-bearing shrinking baseline from the initial repo-wide scan.

### Non-goals
- No changes to `config.py`, `title_match.py`, or any existing lint module.
- No coverage of display strings, log messages, docstrings, or comments.
- Not a replacement for `scripts/test-legacy-title-prefix-literals-scope.sh` (different scope).

### Approach sketch
- New `python/larch/lint/lint_lifecycle_prefix_literal.py`: build token set at runtime from `config.TRACKING_ISSUE_PREFIX_BY_STATE.values()` plus `BUG_PREFIX` from `title_match.py`; AST-walk non-test sources; flag comparison and match positions.
- Allowlist `config.py` and `title_match.py`; skip test files; support `# lint-lifecycle-prefix: ok <reason>` inline suppression.
- Register `("lint", "lifecycle-prefix-literal")` in `python/larch/cli.py` next to sibling lints.
- Add `$(PYTHON) python/cli.py lint lifecycle-prefix-literal` to `py-lint-checks-fast` and `regen-lifecycle-prefix-literal-baseline` make target.
- Seed `python/lifecycle-prefix-literal-baseline.json` via `--write --initial-reason`.

### Surfaces in scope
- `python/larch/lint/lint_lifecycle_prefix_literal.py` (new)
- `python/tests/lint/test_lint_lifecycle_prefix_literal.py` (new)
- `python/larch/cli.py` (registry entry)
- `Makefile` (recipe line, regen target, .PHONY)
- `python/lifecycle-prefix-literal-baseline.json` (new, seeded)

### Open questions
- None.
