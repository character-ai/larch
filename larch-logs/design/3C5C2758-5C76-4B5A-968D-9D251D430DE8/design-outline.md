## Proposed Design Outline

### Goals
- Add regression tests for the retry-dedupe logic in `shard_totals_per_run`.
- Cover both the retried-shard scenario (latest attempt used) and the multi-bash consecutive-row scenario (all rows counted).

### Non-goals
- No changes to production code (`harness_ci_timing.py`).
- No tests for `_split_shard_attempts` directly (end-to-end only via `shard_totals_per_run`).
- No new test helpers or fixtures beyond plain `TimingRow` construction.

### Approach sketch
- Add 3 test functions to `python/test_harness_ci_timing.py` under the existing `shard_totals_per_run` section.
- Test 1: retried shard — duplicate shard runs the same targets, verify only the latest attempt's total is returned.
- Test 2: multi-bash targets — consecutive duplicate target rows are all summed within one attempt.
- Test 3: retried shard with multi-bash — combine both behaviors in a single shard.

### Surfaces in scope
- `python/test_harness_ci_timing.py`

### Open questions
- None.
