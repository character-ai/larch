# scripts/write-run-params.sh - contract

`scripts/write-run-params.sh` writes the `/design` router artifact, `run-params.json`, using `jq -n` and an atomic `mktemp` + `mv` replace.

## Purpose And Callers

Primary callers are `/design` Step 0 and prompt-side tests. `/implement` forwards a caller-computed classification to `/design`, but `/design` remains the writer for the per-run artifact under `$DESIGN_TMPDIR/run-params.json`.

## Invariants

- Runs with `set -euo pipefail`.
- Requires an absolute `--output` path and an existing output directory.
- Requires `--classification <SIMPLE|HARD>` and `--output <absolute-path>`. Both reject a missing or empty argv value with `exit 2` and a `requires a value` stderr line (consistent with the boolean flags below).
- Optional `--reason <text>`, `--source <text>`, `--sketch-budget <0|2|4>`, `--review-budget <full>`, and `--workflow-path <SIMPLE|HARD>` default to JSON null when omitted or passed as an empty string. The parser accepts `--reason ""` / `--source ""` and emits null instead of treating the empty string as a missing argv value.
- Optional `--partition-requested <true|false>`, optional `--brainstorm-requested <true|false>`, and optional `--manual-gate-b <true|false>` default to JSON false when omitted. Each requires a present, non-empty `true`/`false` value when passed on the command line and rejects a missing or empty argv value with `exit 2` (unlike the nullable text flags above, which accept `""` and emit JSON null). See [`skills/design/references/flags.md`](../skills/design/references/flags.md) for the public `-p` / `--partition`, `--brainstorm`, and `--manual` / `-m` flag semantics wired from `/design` Step 0b.
- Validates `--classification` as `SIMPLE` or `HARD`; any other value is rejected (exit 2).
- Emits schema v3 JSON with these keys: `schema_version`, `design_classification`, `design_classification_reason`, `design_classification_source`, `sketch_budget`, `review_budget`, `workflow_path`, `partition_requested`, `brainstorm_requested`, and `manual_gate_b`.
- Readers must accept `schema_version >= 2` for backward compatibility with older persisted run-params artifacts.
- `manual_gate_b` is consumed only by `skills/design/references/approval-gates.md` Gate B; missing/null readers coerce it to `false`.
- Prints `RUN_PARAMS_WRITTEN=<path>` on success and exits non-zero on validation or write failure.

## Harness

`scripts/test-write-run-params.sh` exercises valid v3 writes, enum rejection for invalid classifications, absolute-output validation, boolean flag validation, missing/empty-value rejection for all five required/boolean flags (`--classification`, `--output`, `--partition-requested`, `--brainstorm-requested`, `--manual-gate-b`), nullable v3 optional-field behavior, exact-name round-trips for `design_classification_reason`, `design_classification_source`, `sketch_budget`, `review_budget`, and `workflow_path`, and the triple-flag `partition_requested` + `brainstorm_requested` + `manual_gate_b` persistence case.

## Edit In Sync

Update this file, `scripts/test-write-run-params.sh`, `skills/design/SKILL.md`, and `skills/design/references/flags.md` whenever the `run-params.json` schema, flag signature, or enum set changes.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
