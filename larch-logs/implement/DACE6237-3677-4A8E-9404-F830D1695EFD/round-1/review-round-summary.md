# Review Round 1

- Mode: `diff`
- 1 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_2: Shard-total dedupe collapses legitimate same-attempt timing rows
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `python/harness_ci_timing.py` deduplicates every duplicate `(run_id, shard, target)` row, including legitimate multiple rows for the same target within one successful attempt. `Makefile` already emits two `LARCH_HARNESS_TIMING` rows for one target (e.g. `test-harness-shards-coverage` at 50s and 1s), so verification shard totals can undercount (report 1s instead of 51s) and rebalance verification can pass an overloaded shard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Sum same-target rows within one job attempt, then dedupe repeated attempts; if attempt boundaries are unavailable, emit unique timing labels for subcommands before deduping.
  - From codex-specialist-edge-cases-output.txt: Deduplicate retries without discarding same-attempt multi-row target cost, for example by preserving per-target repeated rows within the latest attempt or by adding attempt-aware parsing before summing.


