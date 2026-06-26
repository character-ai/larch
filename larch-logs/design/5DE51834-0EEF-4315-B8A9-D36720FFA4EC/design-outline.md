## Proposed Design Outline

### Goals
- Make value-weighted reviewer pruning fire in `/implement` by lowering the activation window from rounds 3–4 to rounds 2–4.
- Fix the docs inconsistency: `docs/point-competition.md` says "unweighted" but the gate uses `weighted_accepted_sum`.

### Non-goals
- Do not change the pruning formulas (`net_prunable`, `floor_prunable`).
- Do not add a separate implement-vs-design code path.
- Do not touch voter scoring, OOS scoring, calibration code, or the upper round cap (`round_num >= 5`).

### Approach sketch
- In `reviewer_prune_filter`: lower guard from `round_num <= 2` to `round_num <= 1`.
- In `prune_window_evaluated`: extend set from `{"3", "4"}` to `{"2", "3", "4"}`.
- In `reviewer_prune_filter`: relax single-reviewer evidence from `len(recent) >= 2` to `len(recent) >= 1` so round-2 pruning can act on one prior round of data.
- In `docs/point-competition.md`: fix "unweighted" wording to reflect value-weighted math.
- Update tests in `python/test_review_pipeline.py` to cover round-2 activation and fix any round-1/2 inactivity assertions.

### Surfaces in scope
- `python/review_pipeline.py`
- `docs/point-competition.md`
- `python/test_review_pipeline.py`

### Open questions
- None.
