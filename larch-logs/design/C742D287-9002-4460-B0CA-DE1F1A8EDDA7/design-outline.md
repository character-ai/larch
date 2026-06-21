## Proposed Design Outline

### Goals
- Make classification-replay scoring apply `LARCH_UNIQUE_FINDER_BONUS`, matching the live tally.
- Keep replayed scoreboards consistent with the live run when the bonus is enabled.

### Non-goals
- No change to live-tally code, the bonus value/default, or the env-var contract.
- No change to the JSONL "by suggestions accepted" count path (not a point replay).
- No behavior change when the bonus is unset (off by default; zero run-log regression).

### Approach sketch
- Read `unique_finder_bonus_from_env()` once per replay surface.
- For an accepted in-scope finding with exactly one reviewer, add the bonus to that sole reviewer; mirror the live rule `len(reviewers) == 1`.
- Fix `voting.py:_scoreboard_points_from_classification` and `progress_report.py:_accepted_reviewers_from_classification`.
- Render fractional points via the shared `format_score` helper where points become non-integer.

### Surfaces in scope
- `python/voting.py` (`_scoreboard_points_from_classification`, feeds `voting scoreboard`).
- `python/progress_report.py` (`_accepted_reviewers_from_classification` -> Top reviewers).
- `python/test_voting.py`, `python/test_progress_report.py` (regression tests).
- `docs/point-competition.md` (one-line note that replay now matches live).

### Open questions
- None.
