## Proposed Design Outline

### Goals
- Add `lint_monkeypatch_facade_binding`: flag `monkeypatch.setattr(M, "name", ...)` where repo module `M` binds `name` only by import.
- Reproduce and catch the #6494 silent-no-op shape; wire into `py-lint-checks-fast` with a shrink-only baseline.

### Non-goals
- No late-attribute-access detection (V1). Those lines use inline suppression.
- No runtime import of scanned modules; static analysis only.
- No edits to existing production lints or unrelated tests beyond baseline/suppression needs.

### Approach sketch
- New module `python/larch/lint/lint_monkeypatch_facade_binding.py`, `main(argv) -> int`, mirroring `lint_tempfile_dir.py` (frozen `Finding`, `Record` TypedDict, `BaselineError`, `--write`/`--initial-reason`).
- AST pass over test files: find `monkeypatch.setattr` calls, resolve first arg to an imported repo module via the file's own imports, locate that module's source under `python/`, parse it, flag attributes bound only by import.
- Handle the dotted-string form `monkeypatch.setattr("pkg.mod.name", ...)`.
- Shrink-only reason-bearing baseline `python/monkeypatch-facade-binding-baseline.json`; inline suppression `# lint-monkeypatch-binding: ok <reason>`.

### Surfaces in scope
- `python/larch/lint/lint_monkeypatch_facade_binding.py` (new)
- `python/larch/cli.py` (registry row)
- `Makefile` (`py-lint-checks-fast` line, `regen-monkeypatch-facade-binding-baseline` target, `.PHONY`)
- `python/tests/lint/test_lint_monkeypatch_facade_binding.py` (new)
- `python/monkeypatch-facade-binding-baseline.json` (new)

### Open questions
- Whether the current repo has live violations (decides whether the baseline ships empty or grandfathered). Resolved mechanically by the repo-wide scan during implementation.
