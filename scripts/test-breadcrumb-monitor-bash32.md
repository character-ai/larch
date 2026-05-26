# test-breadcrumb-monitor-bash32.sh contract

Runs `scripts/test-breadcrumb-monitor.sh` under `/bin/bash` when that binary is
macOS Bash 3.2.

## Args

No arguments.

## Environment

Inherits the harness environment. The child harness allocates its own
`IMPLEMENT_TMPDIR` and temporary files.

## Skip Semantics

If `/bin/bash` is missing or does not report `version 3.2`, prints
`SKIP=no-bash32` and exits `0`.

## Exit Codes

- `0`: skipped or all breadcrumb-monitor assertions passed.
- non-zero: propagated from `test-breadcrumb-monitor.sh`.

Keep this wrapper Bash 3.2-clean; it exists to catch portability regressions in
the monitor and its harness on the macOS system shell.
