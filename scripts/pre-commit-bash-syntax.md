# scripts/pre-commit-bash-syntax.sh - contract

## Purpose

`scripts/pre-commit-bash-syntax.sh` is the parallel `bash -n` (syntax-check)
wrapper invoked by the `bash-syntax-check` pre-commit hook in
`.pre-commit-config.yaml`. On macOS `/bin/bash` is 3.2.57 (Apple's GPLv2-frozen
system bash), so the hook doubles as a bash 3.2 parse-time check for Mac
developers. On Linux the system bash (5.x) catches generic syntax errors.

## Invariants

- Consumes only `"$@"` from pre-commit; file selection stays in `.pre-commit-config.yaml`.
- Zero-args input exits 0 (BSD xargs has no `-r`).
- Forwards filenames as NUL-delimited records via `printf '%s\0' | xargs -0 -n 1`.
- Uses portable CPU-count fallback order: `nproc`, `sysctl -n hw.ncpu`, `getconf`, then `1`.

## Callers

- `.pre-commit-config.yaml` `repo: local` `id: bash-syntax-check` hook (`entry: scripts/pre-commit-bash-syntax.sh`).
- Indirectly: `make lint`, `pre-commit run bash-syntax-check`, `python3 python/cli.py checks run-relevant --site <site> --tmpdir <tmpdir>`, and the GitHub Actions `lint-local` job.

## Edit-in-sync rules

- Keep the `xargs -P` / `-n 1` pattern in sync with `scripts/pre-commit-shellcheck.sh`.
- The CI `bash32-check` job (Linux runner, pinned bash 3.2.57 Docker image) is the authoritative bash 3.2 gate; this hook gives developers the same check at commit time.

## E3 residual scope

This check reads the residual Bash manifest through `python3 python/cli.py residual-bash paths --root "$ROOT"` or the equivalent root-local manifest read. The manifest covers kept hooks, linters, thin wrappers, `scripts/sleep-seconds.sh`, the combine-issues helper, manifest-listed includes when present, and residual harnesses. Terminal shared libraries and retired non-thin helpers are out of scope.
