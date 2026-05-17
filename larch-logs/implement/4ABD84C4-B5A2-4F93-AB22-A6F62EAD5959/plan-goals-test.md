## Goal
Balance CI test-harness shard times by redistributing 3 heavy tests from shard-8

## Implementation Plan
Goal: Rebalance CI test-harness shards by moving 3 heavy tests out of shard-8.

Timing data (local, macOS):
- test-ship-pr: 47s  → move to shard-10 (currently 16s → becomes ~63s)
- test-dispatch-panel: 30s → move to shard-2 (currently 40s → becomes ~70s)
- test-review-and-fix: 16s → move to shard-1 (currently 41s → becomes ~57s)
- shard-8 after: 164s - 47s - 30s - 16s = ~71s (was 164s)


### 1. Makefile test-harnesses-1 (line 30)
Append `test-review-and-fix` at end of existing test list.

### 2. Makefile test-harnesses-2 (line 32)
Append `test-dispatch-panel` at end of existing test list.

### 3. Makefile test-harnesses-8 (line 43)
Remove three tests: `test-dispatch-panel`, `test-review-and-fix`, `test-ship-pr`

### 4. Makefile test-harnesses-10 (lines 48-51)
- Update comment to reflect test-ship-pr addition
- Append `test-ship-pr` to the target line


## Test plan
- make test-harness-shards-coverage (partition invariant — must pass)
- make test-harnesses-8 (should be ~71s locally, ~40s on CI)
- make test-harnesses-10 (should be ~63s locally)
