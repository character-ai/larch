# scripts/write-run-params.sh - contract

`scripts/write-run-params.sh` writes the `/design` run-depth router artifact, `run-params.json`, using `jq -n` and an atomic `mktemp` + `mv` replace.

## Purpose And Callers

Primary callers are `/design` Step 0 and prompt-side tests. `/implement` forwards a caller-computed classification to `/design`, but `/design` remains the writer for the per-run artifact under `$DESIGN_TMPDIR/run-params.json`.

## Invariants

- Runs with `set -euo pipefail`.
- Requires an absolute `--output` path and an existing output directory.
- Requires all schema fields up front: `--classification`, `--reason`, `--source`, `--sketch-budget`, `--review-budget`, `--workflow-path`, and `--output`.
- Validates `--classification` as `TRIVIAL_DOC_ONLY`, `SIMPLE`, or `HARD`.
- Validates `--source` as `caller-forwarded` only (obsolete `router-pre-design` is rejected).
- Validates `--sketch-budget` as `0`, `2`, or `4`.
- Validates `--review-budget` as `quick` or `full`.
- Validates `--workflow-path` as `SIMPLE` or `HARD`.
- Emits JSON with `schema_version=1`, `design_classification`, `design_classification_reason`, `design_classification_source`, `sketch_budget`, `review_budget`, and `workflow_path`.
- Uses `jq --arg` for prose fields so quotes, newlines, and shell-shaped text are JSON data, not syntax.
- Prints `RUN_PARAMS_WRITTEN=<path>` on success and exits non-zero on validation or write failure.

## Harness

`scripts/test-write-run-params.sh` exercises valid writes, JSON escaping for prose, enum rejection, absolute-output validation, and the quick/full precedence budget examples used by the prompt-side router docs.

## Edit In Sync

Update this file, `scripts/test-write-run-params.sh`, and `skills/design/SKILL.md` whenever the `run-params.json` schema or enum set changes.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
