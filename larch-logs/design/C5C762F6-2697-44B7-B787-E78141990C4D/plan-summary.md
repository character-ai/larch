Renames the dev-only `/rebalance-test-harnesses` skill to `/rebalance-tests` (hard move, no alias) and adds Python pytest matrix shard rebalancing.

**Three jobs, one feature:**
- **Rename**: `git mv` the skill dir to `.claude/skills/rebalance-tests/`, delete the old dir, update the path pin in `python/test_rebalance_script.py` and prose in `docs/linting.md`. Five live surfaces only.
- **New Python timing parser**: `python/pytest_ci_timing.py` mirrors `python/harness_ci_timing.py`. It parses `--durations=0` `call` rows from `python-tests` job logs into `nodeid -> median seconds`.
- **Assignment map honored by pytest**: `python/pytest_sharding.py` gains `load_shard_assignments` + `select_shard_nodeids`; `python/conftest.py` selects by `item.nodeid`. A checked-in `python/shard-assignments.json` starts `{}` (round-robin only), fails closed on bad JSON, and falls back to full round-robin when the map's max shard id does not equal the active shard count. Coverage can never silently drop.

**Unified runner**: `rebalance.py` gains `--kind {harness,python,all}` (default `all`) and `--n-python-shards` (default `4`). `--kind harness` stays behavior-equivalent. `--kind all` packs both in memory, writes `Makefile` and validates the partition before writing the assignments JSON, stages both artifacts in one commit/PR, and reverts only written paths on failure. Verification is asymmetric: harness stays warning-only (exit 0); Python fails closed (non-zero on zero rows, missing shard coverage, or spread over threshold).
