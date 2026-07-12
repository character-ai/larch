## Proposed Design Outline

### Goals
- Extract the shared per-item tally adjudication loop into one module consumed by both `review_tally.py` and `plan_review_tally.py`.
- Collapse `_finding_oos_reroute_marker` to one definition; remove the duplicate.
- Add a new test file covering the shared engine; keep the three named tests passing unchanged.

### Non-goals
- Changing the public API of `review_tally.py` or `plan_review_tally.py` as seen by their callers.
- Touching `self_review_tally.py`, `round_runner.py`, `review_and_fix.py`, or `calibration_replay.py` beyond call-site updates if any are needed.
- Unifying the TSV schemas (code-review and plan-review classification headers remain family-specific).

### Approach sketch
- Add `python/larch/review/tally_engine.py` with shared per-item adjudication logic: OOS detection, `neutral_rescued`, `fileable_oos`, `score_result`, and `_finding_oos_reroute_marker`.
- Family-specific parts (vote source, TSV row format, score row computation) stay in their respective modules as hooks/parameters.
- `review_tally.py` and `plan_review_tally.py` import and delegate to `tally_engine`; net line reduction from eliminating duplicated logic.
- Add `python/tests/review/test_tally_engine.py` covering the shared adjudication primitives.

### Surfaces in scope
- `python/larch/review/review_tally.py` (firm heading)
- `python/larch/review/plan_review_tally.py` (firm heading)
- `python/larch/review/tally_engine.py` (new module)
- `python/tests/review/test_tally_engine.py` (new tests)

### Open questions
- None.
