## Proposed Design Outline

### Goals
- Add `compute_voter_severity_distribution` to `python/voting.py`, parallel to `compute_voter_agreement`.
- Surface the per-voter severity table in the `/voter-calibration` report and in live tally output for both review and plan-review tallies.
- Flag voters whose YES-vote high-severity rate exceeds a configurable threshold (default 0.90) as uncalibrated.

### Non-goals
- No change to live voting decisions, spawning, thresholds, or reviewer points.
- No modification of existing `compute_voter_agreement` signature or tally column format.
- No new output files; severity table appends inline to existing tally and report output.

### Approach sketch
- Extend voter dicts (in `voter_agreement_row_from_panel` and `voter_agreement_rows_from_tsv`) to carry per-voter severity on YES votes.
- Add `compute_voter_severity_distribution(rows, *, high_severity_threshold=0.90)` and `render_voter_severity_scoreboard(records)` in `voting.py`.
- Update `voter-calibration.py`: add `--high-severity-threshold` flag; call new aggregator; render new section.
- Update `review_tally.py` and `plan_review_tally.py`: collect severity alongside existing agreement rows; append severity scoreboard after agreement scoreboard.

### Surfaces in scope
- `python/voting.py`
- `python/review_tally.py`
- `python/plan_review_tally.py`
- `skills/voter-calibration/scripts/voter-calibration.py`
- `python/test_voting.py` (new unit tests)
- `python/test_review_tally.py` and/or `python/test_plan_review.py` (integration tests)

### Open questions
- None.
