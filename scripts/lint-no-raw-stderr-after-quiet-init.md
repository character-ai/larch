# lint-no-raw-stderr-after-quiet-init.py

`scripts/lint-no-raw-stderr-after-quiet-init.py` enforces S041/no-raw-stderr-after-quiet-init.

It scans `.sh` files under `scripts/`, `hooks/`, and `skills/*/scripts/`.
Once a file contains an actual `larch_quiet_init` call, later `echo`,
`printf`, or `cat` writes to raw stderr are violations because FD 2 points at
the quiet log after init. User-visible diagnostics must use `larch_err` or
`larch_errf`.

Pre-init diagnostics remain allowed for source/bootstrap failures before
`scripts/lib-quiet.sh` is available. Function definitions, quoted text, comments,
and heredoc bodies do not activate the rule.

The hook is registered in `.pre-commit-config.yaml` as
`lint-no-raw-stderr-after-quiet-init`. The regression harness is
`scripts/test-lint-no-raw-stderr-after-quiet-init.sh`, wired into `make lint`
via `test-lint-no-raw-stderr-after-quiet-init`.
