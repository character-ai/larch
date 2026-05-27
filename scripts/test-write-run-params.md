# test-write-run-params.sh

Regression harness for v2 `/design` `run-params.json`.

Coverage:

- Valid `SIMPLE` and `HARD` writes with schema version 2.
- Rejection of invalid `design_classification`, including `TRIVIAL_DOC_ONLY`.
- Rejection of relative output paths.
- Validation of `--partition-requested`, `--brainstorm-requested`, and `--manual-gate-b`.
- Explicit `--manual-gate-b true` and `--manual-gate-b false` persistence.
- Triple-flag persistence: `--partition-requested true` plus `--brainstorm-requested true` plus `--manual-gate-b true`.

## Callers

Run directly with `bash scripts/test-write-run-params.sh` or through `make test-write-run-params`. The target is part of `make lint` via the `test-harnesses-N` shard partition.

## Edit In Sync

Update this harness with `scripts/write-run-params.sh`, `scripts/write-run-params.md`, and any prompt-side schema docs that consume `run-params.json`.
