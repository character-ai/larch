# test-gate-b-dedup-plan.sh

Offline harness for `gate-b-dedup-plan.sh`.

## Cases

1. `--snapshot-trailers` writes `.gate-b-optional-trailer-keys` and companion `.values`.
2. `--dedup` without prior snapshot exits **3** (fail closed).
3. `--dedup` after snapshot removes duplicate body lines and preserves optional trailers.
4. Empty snapshot rejects newly introduced optional trailers on `--dedup` (exit **1**).
5. Snapshot rejects trailer value changes on `--dedup` (exit **1**, plan restored).
