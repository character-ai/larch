# launch-codex-exec.sh

Generic auth-wired Codex prompt launcher for research lanes, voters, judges, and lint-fix.

## Flags

- `--output PATH` (absolute, validated via `validate_meta_scalar_path`)
- `--timeout SECONDS`
- exactly one of `--prompt STRING` / `--prompt-file PATH`
- `--workdir PATH` (default `$PWD`)
- repeatable `--add-dir PATH` (defaults to `--add-dir "$workdir"` when omitted)
- `--sandbox full-auto|read-only`
- `--with-effort`
- `--usage-label LABEL` (default `codex_exec`)
- `--timing-task-kind KIND` (default `codex-exec`)

## Exit codes

- `0` — wrapper completed; inspect `LAUNCHER_EXIT` on stdout for Codex outcome
- `2` — argv / unsafe `--output` before sidecar I/O

## Harness

`scripts/test-launch-codex-exec.sh`
