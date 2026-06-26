## Proposed Design Outline

### Goals
- Add a `standing_score` field to voter severity records, computed from `high_rate` vs the calibration threshold.
- Tie each voter's high-severity weight in the `+2/+1` tally to their corpus-derived standing score.
- Document voter standing in `docs/point-competition.md`.

### Non-goals
- Do not change YES/NO quorum rules (acceptance thresholds unchanged).
- Do not change voter spawning, pruning, or token allocation.
- Do not re-expose proposer-controlled `body_severity`.

### Approach sketch
- In `compute_voter_severity_distribution`: add `standing_score = max(0.0, 1.0 - high_rate / threshold)` per voter record.
- In `render_voter_severity_scoreboard`: add a `Standing` column.
- Add `voter_weights: Iterable[float] | None = None` to `accepted_finding_points_from_severities`; weight each YES voter's high-severity contribution by its standing score.
- Both tally callers (`plan_review_tally.py`, `review_tally.py`) read an optional env var `LARCH_VOTER_CALIBRATION_FILE` (path to precomputed JSON); when absent all weights default to `1.0` (backward compatible).
- Add `--calibration-json FILE` to `voter-calibration.py` to export machine-readable standings.
- Define `LARCH_VOTER_CALIBRATION_FILE` in `python/config.py` per guideline G-Cfg-1.

### Surfaces in scope
- `python/voting.py`
- `python/plan_review_tally.py`
- `python/review_tally.py`
- `python/config.py` (new env-var constant)
- `skills/voter-calibration/scripts/voter-calibration.py`
- `docs/point-competition.md`
- `python/test_voting.py`

### Open questions
- None.
