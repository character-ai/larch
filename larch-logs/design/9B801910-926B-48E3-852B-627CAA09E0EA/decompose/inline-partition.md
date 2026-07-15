## Pieces

### Piece 1: Lint module, tests, and registration
- Scope: python/larch/lint/lint_tmpdir_arg_env_fallback.py, python/tmpdir-arg-env-fallback-baseline.json, python/tests/lint/test_lint_tmpdir_arg_env_fallback.py, python/larch/cli.py, python/lint-module-manifest.json, Makefile
- Firm-headings: python/larch/lint/lint_tmpdir_arg_env_fallback.py, python/tmpdir-arg-env-fallback-baseline.json, python/tests/lint/test_lint_tmpdir_arg_env_fallback.py, python/larch/cli.py, python/lint-module-manifest.json, Makefile
- Acceptance: python3 -m pytest python/tests/lint/test_lint_tmpdir_arg_env_fallback.py; python3 python/cli.py lint tmpdir-arg-env-fallback; make py-lint-checks-fast includes new check; module-manifest lint passes
- Dependencies: none
- Size estimate: 300 lines

### Piece 2: Production site fixes and docs
- Scope: python/larch/state/_corpus.py, python/larch/state/admission.py, python/larch/issue/file_oos.py, python/larch/implement/dispatch_step2.py, python/larch/implement/scope_disposition.py, python/larch/bgjob/cli.py, python/tests/bgjob/test_bgjob_cli.py, docs/linting.md
- Firm-headings: docs/linting.md, python/larch/state/_corpus.py, python/larch/state/admission.py, python/larch/issue/file_oos.py, python/larch/implement/dispatch_step2.py, python/larch/implement/scope_disposition.py, python/larch/bgjob/cli.py, python/tests/bgjob/test_bgjob_cli.py
- Acceptance: python3 python/cli.py lint tmpdir-arg-env-fallback exits 0; python3 -m pytest python/tests/bgjob/test_bgjob_cli.py passes
- Dependencies: blocked-by Piece 1
- Size estimate: 140 lines
