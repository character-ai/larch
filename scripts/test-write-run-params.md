# scripts/test-write-run-params.sh - contract

`scripts/test-write-run-params.sh` regression-tests `scripts/write-run-params.sh`, the shared writer for `/design` `run-params.json`.

## Coverage

- Valid schema write with JSON escaping for quotes, newlines, and shell-shaped prose.
- Rejection of invalid `design_classification` and `sketch_budget` values.
- Rejection of relative `--output` paths.
- Rejection of invalid `--partition-requested` / `--brainstorm-requested` / `--manual-gate-b` enum tokens.
- Representation of the `--full` + `--quick` budget combination (`sketch_budget=4`, `review_budget=quick`).
- Representation of the `TRIVIAL_DOC_ONLY` zero-sketch path (asserts `partition_requested`, `brainstorm_requested`, and `manual_gate_b` default false).
- Explicit `--manual-gate-b true` and `--manual-gate-b false` persistence.
- Triple-flag persistence: `--partition-requested true` plus `--brainstorm-requested true` plus `--manual-gate-b true` (FINDING_15 recovery-path coverage).

## Callers

Run directly with `bash scripts/test-write-run-params.sh` or through `make test-write-run-params`. The target is part of `make lint` via the `test-harnesses-N` shard partition.

## Edit In Sync

Update this harness with `scripts/write-run-params.sh`, `scripts/write-run-params.md`, and any prompt-side schema docs that consume `run-params.json`.
