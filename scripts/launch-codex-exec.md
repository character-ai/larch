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
- `--trusted-instructions-file PATH` — write trusted `instructions` into temp `CODEX_HOME/config.toml` before appending stripped operator config (drops any existing top-level `instructions` from `~/.codex/config.toml`)

## Exit codes

- `0` — wrapper completed; inspect `LAUNCHER_EXIT` on stdout for Codex outcome
- `2` — argv / unsafe `--output` before sidecar I/O

## Runtime Contract

The launcher prepares a temp `CODEX_HOME`, applies the shared Codex auth setup, resolves model args through `agent-model-args.sh`, and invokes `run-external-agent.sh` with `RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done`. It writes:

- `${output}` for the final Codex message
- `${output}.events.jsonl` for Codex JSON events
- `${output}.sidecar` for launcher stderr / parser diagnostics
- `${output}.prompt` for retry prompt replay
- `${output}.meta` with `OUTER_LAUNCHER_KIND=codex-exec`, sandbox, effort, usage label, timing kind, and `OUTER_LAUNCHER_ADD_DIRS_JSON`
- `${output}.token-record` for best-effort Codex token usage. The sidecar is cleared immediately after `--output` validation, before auth/model preflight can emit a stdout envelope. When model resolution succeeds, the sidecar includes `MODEL=<resolved Codex model>`.

`--add-dir` metadata is serialized without relying on `jq`; if serialization cannot be represented safely without `jq`, the launcher logs a warning and records workdir-only retry metadata so replay does not write lossy `[]` metadata. After post-processing, `${output}.inner.done` is promoted to `${output}.done` and stdout emits `LAUNCHER_EXIT=<codex-exit>` plus `OUTPUT=<path>`.
Stdout also emits `TOKEN_RECORD=<path>`. Callers own exactly-once ingestion into `token-report.ndjson` and any active token ledger.

## Harness

`scripts/test-launch-codex-exec.sh` covers launcher references, timing allow-list registration, happy-path `LAUNCHER_EXIT`, auth/preflight failure bundles, inner sentinel promotion, outer retry metadata, add-dir round trips, and temp `CODEX_HOME` cleanup.
