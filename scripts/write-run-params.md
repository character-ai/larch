# scripts/write-run-params.sh - contract

`scripts/write-run-params.sh` writes the `/design` router artifact, `run-params.json`, using `jq -n` and an atomic `mktemp` + `mv` replace.

## Purpose And Callers

Primary callers are `/design` Step 0 and prompt-side tests. `/implement` forwards a caller-computed classification to `/design`, but `/design` remains the writer for the per-run artifact under `$DESIGN_TMPDIR/run-params.json`.

## Invariants

- Runs with `set -euo pipefail`.
- Requires an absolute `--output` path and an existing output directory.
- Requires `--classification <SIMPLE|HARD>` and `--output <absolute-path>`.
- Optional `--partition-requested <true|false>`, optional `--brainstorm-requested <true|false>`, and optional `--manual-gate-b <true|false>` default to JSON false. See [`skills/design/references/flags.md`](../skills/design/references/flags.md) for the public `-p` / `--partition`, `--brainstorm`, and `--manual` / `-m` flag semantics wired from `/design` Step 0b.
- Validates `--classification` as `SIMPLE` or `HARD`; `TRIVIAL_DOC_ONLY` is rejected.
- Emits v2 JSON only: `schema_version`, `design_classification`, `partition_requested`, `brainstorm_requested`, and `manual_gate_b`.
- Does not emit derived or legacy fields: no `quick_mode`, `sketch_budget`, `review_budget`, `workflow_path`, `design_classification_source`, or `design_classification_reason`.
- `manual_gate_b` is consumed only by `skills/design/references/approval-gates.md` Gate B; missing/null readers coerce it to `false`.
- Prints `RUN_PARAMS_WRITTEN=<path>` on success and exits non-zero on validation or write failure.

## Harness

`scripts/test-write-run-params.sh` exercises valid v2 writes, enum rejection including `TRIVIAL_DOC_ONLY`, absolute-output validation, `--partition-requested` / `--brainstorm-requested` / `--manual-gate-b` validation, and the triple-flag `partition_requested` + `brainstorm_requested` + `manual_gate_b` persistence case.

## Edit In Sync

Update this file, `scripts/test-write-run-params.sh`, and `skills/design/SKILL.md` whenever the `run-params.json` schema or enum set changes.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
