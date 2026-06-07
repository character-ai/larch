# pre-commit-bash-syntax.sh

Parallel `bash -n` (syntax-check) wrapper for the `bash-syntax-check`
pre-commit hook. Receives filenames from pre-commit and runs `bash -n`
on each in parallel via `xargs -P`.

On macOS, `/bin/bash` is 3.2.57 (Apple's GPLv2-frozen system bash), so
local commits on Mac get a real bash 3.2 parse-time check. On Linux the
system bash (5.x) is used instead, still catching generic syntax errors.

The CI `bash32-check` job (macOS runner) provides the authoritative bash
3.2 syntax gate. This hook gives developers the same check at commit time
without waiting for CI.

## Primary callers

- `.pre-commit-config.yaml` `bash-syntax-check` hook

## Makefile target

None — invoked only through pre-commit.

## Harness

None — behaviour is trivially `bash -n` on each file; tested implicitly
by the `bash32-check` CI job and local `pre-commit run --all-files
bash-syntax-check`.

## Edit-in-sync

Keep the `xargs -P` pattern in sync with `scripts/pre-commit-shellcheck.sh`.
