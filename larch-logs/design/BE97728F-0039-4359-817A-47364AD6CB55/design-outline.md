## Proposed Design Outline

### Goals
- Thread `dir=<run-scoped-tmpdir>` into the 15 fixable sites where a session tmpdir is in scope, eliminating ambient `$TMPDIR` dependency for those calls.
- Add an AST-based lint (`lint_tempfile_dir.py`) that flags new no-`dir=` tempfile calls, with a reason-bearing JSON baseline for the 22 intentional or un-fixable sites.
- Wire the lint into `py-lint-checks-fast` with a `regen-tempfile-dir-baseline` Makefile target.

### Non-goals
- The "validate and repair `$TMPDIR`" helper (optional hardening from #6259 direction) is out of scope.
- Fixing sites in `python/tests/` (excluded by issue scope and lint scope).
- Fixing sites in Bash scripts.

### Approach sketch
- **Site sweep**: for each of the 15 fixable sites, thread or read the enclosing run-scoped tmpdir (`design_tmpdir`, `review_tmpdir` env var, `log_root.parent`, or `canonical_tmp`). Minimal surgical changes; no new cross-module plumbing beyond param threading.
- **Baseline**: write `python/tempfile-dir-baseline.json` with one entry per baseline site; each entry carries a short reason string per G-Enf-2 / G-Py-11.
- **Lint module**: `python/larch/lint/lint_tempfile_dir.py` walks AST nodes for `tempfile.mkstemp`, `mkdtemp`, `NamedTemporaryFile`, `TemporaryDirectory` calls lacking a `dir=` keyword argument, checks against the baseline, and exits non-zero on new violations.
- **Makefile + CLI**: one `py-lint-checks-fast` entry and a `regen-tempfile-dir-baseline` target; CLI verb `lint tempfile-dir`.
- **Tests**: `python/tests/lint/test_lint_tempfile_dir.py` covers clean code, violation detection, baseline suppression, and baseline shrink-only enforcement.

### Surfaces in scope
- `python/larch/lint/lint_tempfile_dir.py` (new)
- `python/tests/lint/test_lint_tempfile_dir.py` (new)
- `python/tempfile-dir-baseline.json` (new)
- `Makefile` (lint entry + regen target)
- `python/larch/cli.py` (new verb registration)
- 15 fixable source files (surgical `dir=` threading only)

### Open questions
- None.
