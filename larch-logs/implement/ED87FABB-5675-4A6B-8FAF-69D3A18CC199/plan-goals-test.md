## Goal
Split the test-harnesses-2 CI shard (currently ~97s) into two shards to reduce max CI time.

## Implementation Plan
Move test-launch-review (66s) to new shard 8, rebalance shard 2 with tests from shards 1 and 4.

Modify Makefile: update .PHONY, test-harnesses umbrella, shard lines 1/2/4/7, add shard 8.
Modify .github/workflows/ci.yaml: extend matrix from [1..7] to [1..8].

## Test plan
Run `make test-harness-shards-coverage` to verify partition invariant passes after the changes.
