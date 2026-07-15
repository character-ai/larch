# test-harness-shards-coverage.sh

Regression harness for Makefile `test-harnesses-N` shard membership. It builds a
unified direct-Bash-leaf inventory (recipe-bearing `test-*` targets with no
pytest, plus `*-bash-harness` leaves), then verifies each leaf is assigned to
exactly one shard, rejects aggregates / pytest recipes / unknown non-leaves in
shard lists, checks the umbrella target references all shard targets, and
requires the shard containing this guard to list it first so partition failures
surface before longer harness work. Keep this sibling doc in sync with the
harness whenever shard parsing or Makefile target contracts change.
