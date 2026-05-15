# test-lint-no-raw-stderr-after-quiet-init.sh

Regression harness for `scripts/lint-no-raw-stderr-after-quiet-init.py`.

The harness creates temporary known-good and known-bad shell fixtures under the
same path scopes as the pre-commit hook: `scripts/`, `hooks/`, and
`skills/*/scripts/`. It verifies that pre-init raw stderr is allowed, post-init
`larch_err`/`larch_errf` is allowed, post-init `echo`/`printf`/`cat >&2` is
reported as S041, and quoted/function/heredoc text does not accidentally
activate the rule.

Run directly with `bash scripts/test-lint-no-raw-stderr-after-quiet-init.sh` or
through `make test-lint-no-raw-stderr-after-quiet-init`.
