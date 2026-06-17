## Proposed Design Outline

### Goals
- Bring Bucket 1's 9 multi-target pytest files to strict partitions and add each to `ENFORCED`.
- Capture the headline CI-time win: stop re-running each full file under multiple target names.
- Keep `make test-harness-shards-coverage` green.

### Non-goals
- Bucket 2's 5 heavier already-sliced files (deferred to a follow-up).
- Shard wall-time rebalancing in this PR; sequenced as a tracked `/rebalance-tests` follow-up.
- Editing pytest test bodies or test logic.

### Approach sketch
- Per file: enumerate its current `test-*` targets; classify each as pure-duplicate vs semantically distinct (preserve the `test_run_logs.py` `env -u LARCH_VERIFY_MANIFEST` distinction).
- Retire genuine duplicate full-file targets to one canonical target; update Makefile `test-harnesses-N` membership and `.PHONY`.
- Slice the rest into disjoint `-k` / node-id selections (one `not (...)` catch-all per file); avoid filename-keyword collisions.
- Add each cleanly-partitioned file to `ENFORCED` in `scripts/lint-harness-pytest-partition.py`; refresh its docstring.
- File the rebalance follow-up issue.

### Surfaces in scope
- `Makefile` — Bucket-1 `test-*` recipe targets, `test-harnesses-N` shard membership, `.PHONY`.
- `scripts/lint-harness-pytest-partition.py` — `ENFORCED` tuple + docstring (`scripts/test-harness-shards-coverage.sh` is the validator; reads membership from the Makefile, no edit expected).
- A tracked follow-up issue for `/rebalance-tests --kind harness`.

### Open questions
- None.
