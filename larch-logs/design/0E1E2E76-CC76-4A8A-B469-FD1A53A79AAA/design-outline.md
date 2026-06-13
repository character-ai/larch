## Proposed Design Outline

### Goals
- Fix BEFORE table to compare the same shard indices as AFTER (use `new_shards`, not `current_shards`).
- Fix PR body "before spread" to reflect the new layout's estimated spread.
- Add a feasibility preflight warning (warn+continue) when the heaviest single target exceeds `ideal_shard + threshold/2`.

### Non-goals
- No changes to the LPT packing algorithm.
- No abort-on-infeasible flag; warn+continue is the correct behavior.
- No splitting of `test-stall-recovery-report.sh` (tracked as a separate follow-up).

### Approach sketch
- Line 474: replace `current_shards` with `new_shards` in `_print_shard_table("BEFORE ...")`.
- Lines 403-406: replace `current_shards` with `new_shards` in the `baseline_spread` computation.
- After `medians = compute_medians(...)` (step 2, ~line 329): insert feasibility preflight block (warn+continue if infeasible; print top-5 heaviest targets when the warning fires).

### Surfaces in scope
- `.claude/skills/rebalance-test-harnesses/scripts/rebalance.py`

### Open questions
- None.
