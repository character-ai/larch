# lib-phantom-probe.sh

Sourced-only library loaded by `scripts/rebase-checkpoint-probe.sh` and `scripts/phantom-probe-with-warn.sh`.

## `phantom_probe_with_warn <step-token>`

Runs `check-phantom-dirty.sh`, parses `STATUS` / `REASON` / `PHANTOM_COUNT` / `PHANTOM_PATHS_FILE`, re-emits them as `PHANTOM_STATUS` (mirrors `STATUS=`) plus companion keys, and on `STATUS=phantom|unknown` invokes `append-execution-issue.sh` with the same Warnings entries as `skills/implement/SKILL.md` historically spelled inline.

## FINDING_1 — append failure diagnostics

When `append-execution-issue.sh` exits non-zero, the library captures **combined stdout+stderr** (`2>&1`), prefers the first `ERROR=` line (contract stream / stdout-first), then falls back to the non-`ERROR=` tail of the combined capture for a folded `PHANTOM_APPEND_WARN_ERROR` KV (newlines collapsed to spaces). It then best-effort appends a secondary Warnings line (`phantom warning append failed`) via `append-execution-issue.sh` with output discarded.

Nested helpers run with `LARCH_QUIET_DISABLE=1` so machine-readable KVs land on the wrapper’s stdout for orchestrator parsing.
