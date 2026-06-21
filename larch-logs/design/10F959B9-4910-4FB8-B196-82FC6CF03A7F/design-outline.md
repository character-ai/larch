## Proposed Design Outline

### Goals
- Price an in-scope `neutral` finding at −0.25 (was 0) so it costs more than silence, tightening the raise-threshold toward P(accept) > 0.5.
- Keep neutral pricing consistent across both /design plan-review and /review code-review scoreboards.
- Update the point-competition docs to match.

### Non-goals
- No change to accepted (+2/+1), rejected (−1), or silence (0).
- No change to OOS scoring: OOS neutral stays 0 (left to #4776).
- No change to conditional pruning (#4772) or precision token allocation (#4771).

### Approach sketch
- Add one shared constant in `python/voting.py` (e.g. `NEUTRAL_FINDING_COST = 0.25`) so the value cannot drift across call sites.
- Subtract `NEUTRAL_FINDING_COST × in-scope-neutral-count` in the per-reviewer Score formula, which is duplicated in `plan_review_tally.py` and `review_tally.py`.
- Update `voting.py::_scoreboard_points_from_classification` (the `voting scoreboard` CLI path) to match; in-scope neutral only.
- Scores become fractional; render cleanly (drop a trailing `.0`).

### Surfaces in scope
- `python/voting.py` — shared constant, scoreboard-CLI delta, score-format helper.
- `python/plan_review_tally.py`, `python/review_tally.py` — Score formula.
- `docs/point-competition.md`, `skills/shared/voting-protocol.md`, `skills/design/references/plan-review.md` — docs.
- `python/test_voting.py` (+ tally test modules) — regression.

### Open questions
- None.
