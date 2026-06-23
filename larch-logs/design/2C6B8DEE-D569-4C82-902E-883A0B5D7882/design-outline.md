## Proposed Design Outline

### Goals
- Add a concrete severity rubric to voter prompts so voters have explicit examples for each level.
- Change `accepted_finding_points_from_severities` from "any YES voter high" to "majority of YES voters rate high."

### Non-goals
- Do not revert to `body_severity` (proposer-set severity).
- Do not change the +1/+2 point values themselves.
- Do not change the necessity gate or accept/reject logic.

### Approach sketch
- Add rubric prose to `python/rendering.py` voter prompt rendering (both `render voter` and `render plan-review` paths).
- Rewrite `accepted_finding_points_from_severities` in `python/voting.py` to count YES-voter high ratings and return +2 only when majority exceed 50%.
- Update `skills/shared/voting-protocol.md` scoring table prose to match the new majority semantics.
- Update tests in `python/test_voting.py`, `python/test_review_tally.py`, and `python/test_plan_review.py`.

### Surfaces in scope
- `python/voting.py` (aggregation function)
- `python/rendering.py` (voter prompt rubric prose)
- `skills/shared/voting-protocol.md` (scoring table description)
- `python/test_voting.py`, `python/test_review_tally.py`, `python/test_plan_review.py`

### Open questions
- None.
