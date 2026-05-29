# test-write-run-params.sh

Regression harness for `/design` `run-params.json`.

Coverage:

- Valid `SIMPLE` and `HARD` writes.
- Rejection of invalid `design_classification`, including `TRIVIAL_DOC_ONLY`.
- Rejection of relative output paths.
- Missing/empty-value rejection for all required and boolean flags: `--classification`, `--output`, `--partition-requested`, `--brainstorm-requested`, and `--manual-gate-b` (each exits 2 with a `requires a value` message).
- Explicit `--manual-gate-b true` and `--manual-gate-b false` persistence.
- Triple-flag persistence: `--partition-requested true` plus `--brainstorm-requested true` plus `--manual-gate-b true`.

## Callers

Run directly with `bash scripts/test-write-run-params.sh` or through `make test-write-run-params`. The target is part of `make lint` via the `test-harnesses-N` shard partition.

## Edit In Sync

Update this harness with `scripts/write-run-params.sh`, `scripts/write-run-params.md`, and any prompt-side schema docs that consume `run-params.json`.
