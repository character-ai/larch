# lib-prune-decision.sh

Shared reviewer-prune decision helpers for implement and design review paths.
Callers run `reviewer-prune.sh filter`, parse its machine-readable KVs, then
call `derive_prune_status` instead of deriving caller-local status labels.

## Status precedence

`derive_prune_status(prune_active, filter_rc, prune_fail_open, pruned_count, panel_pruned_empty, prune_evaluated)` returns the first matching status:

1. `failed` when the filter exits non-zero or emits `PRUNE_FAIL_OPEN=true`.
2. `pruned-empty` when `PANEL_PRUNED_EMPTY=true`.
3. `skipped` when pruning is inactive or the round is outside the evaluated pruning window.
4. `active-dropped` when pruning evaluated and dropped at least one combo.
5. `active-kept-all` when pruning evaluated and kept every combo.

Advisory `WARN` lines are operator-visible only. They never imply `failed`;
only non-zero filter rc or the explicit `PRUNE_FAIL_OPEN=true` machine signal do.

## Window and schema

`prune_window_evaluated(round_num)` returns `true` only for prune rounds 3 and 4.
Out-of-window callers should force `PRUNE_ACTIVE=false` before deriving status so
concise logs read as `skipped`, not `active-kept-all`.

`write_prune_decision_env(dest, round, prune_active, prune_status, panel_full, eligible, pruned_count, pruned_combos, panel_pruned_empty)` atomically writes:

```text
ROUND
PRUNE_ACTIVE
PRUNE_STATUS
PANEL_FULL
ELIGIBLE
PRUNED_COUNT
PRUNED_COMBOS
PANEL_PRUNED_EMPTY
```

`ROUND` is the prune/filter counter passed to `reviewer-prune.sh filter`; artifact
directory placement is the caller's responsibility. Design may therefore write
under `plan-review/round-${ROUND_NUM}/` while `ROUND=` contains a different
`PRUNE_ROUND_NUM`.
