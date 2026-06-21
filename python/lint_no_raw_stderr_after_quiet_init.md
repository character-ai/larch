# python/lint_no_raw_stderr_after_quiet_init.py contract

`python3 python/cli.py lint no-raw-stderr-after-quiet-init` enforces S041/no-raw-stderr-after-quiet-init.

After a script calls `larch_quiet_init`, caller-visible diagnostics must use `larch_err` or `larch_errf`. Raw `echo`, `printf`, or `cat` writes to FD 2 are flagged.

## Caller surface

Primary callers are the local pre-commit hook, `make test-lint-no-raw-stderr-after-quiet-init`, and manual local runs. The bash harness remains `scripts/test-lint-no-raw-stderr-after-quiet-init.sh`.

## Invariants

- Exit codes stay `0` for clean, `1` for violations, and `2` for internal errors.
- Scope stays runtime shell files under `scripts/`, `hooks/`, and `skills/<name>/scripts/`.
- Function definitions, quoted text, and heredoc bodies do not trigger quiet-init state or raw-stderr matches.
- `--root` is the only option. Positional filenames are rejected by argparse.

## Edit-in-sync

Update this contract and the harness with behavior changes.
