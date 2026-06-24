## Proposed Design Outline

### Goals
- Add `weighted_accepted` to `PruneRoundCounts` and the prune ledger (new `weighted_accepted_count` column).
- Replace the unweighted net (`accepted_sum - rejected_sum`) in `reviewer_prune_filter` with a value-weighted net (`weighted_accepted_sum - rejected_sum`), where high-severity accepted findings count double.
- Preserve backward compat: old 7-column ledger files degrade gracefully (default `weighted_accepted = accepted`).

### Non-goals
- Do not change the 1/3 acceptance floor formula (still uses unweighted `accepted_sum`).
- Do not change prune activation windows (rounds 3-4 only).
- Do not add a runtime feature flag; gating is via the dependency issue landing first.

### Approach sketch
- Extend `PruneRoundCounts` frozen dataclass with `weighted_accepted: int = 0` (aligns with G-Py-1).
- Add `_accepted_severity_weight(row, plan_mode)` helper: returns 2 when `body_severity` (plan mode) or voter majority is high-severity, else 1.
- Extend `_prune_ledger_header()` to 8 columns; update `_well_formed_prune_ledger_row` to accept 7 (legacy) or 8 columns.
- Update `_read_classification_counts` to compute `weighted_accepted` per slot using the helper.
- Update `_ledger_history` to read `weighted_accepted_count` when present; default to `accepted` otherwise.
- Update `reviewer_prune_filter` to compute `weighted_accepted_sum` and use it for the net check.

### Surfaces in scope
- `python/review_pipeline.py` (all prune functions)
- `python/test_review_pipeline.py` (header assertions, new severity-weighting tests)
- `python/test_plan_review_round.py` (header assertions)

### Open questions
- None.
