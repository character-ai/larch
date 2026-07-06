# test-harness-shards-coverage.sh

Regression harness for Makefile `test-harnesses-N` shard membership. It verifies each harness target is assigned to exactly one shard, the umbrella target references all shard targets, and the shard containing this guard lists it first so partition failures surface before longer harness work. Keep this sibling doc in sync with the harness whenever shard parsing or Makefile target contracts change.
