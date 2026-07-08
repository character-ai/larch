## Proposed Design Outline

### Goals
- Accept `OOS_k:` vote lines when tallying a `FINDING_k` ballot item (and vice versa), eliminating per-item JUDGE_ERROR from voter id relabeling.
- Guard against mis-assignment: alias only when the aliased id is not itself a ballot id.
- Add regression tests covering the alias path, the collision guard, and unchanged existing behavior.

### Non-goals
- Change the aggregator's ballot heading grammar (ballot hygiene) in this issue.
- Modify voter prompts or retry logic.
- Change any external-facing CLI surface or output schema.

### Approach sketch
- Add `alias_ballot_id(ballot_id, ballot_id_set)` helper to `voting.py` that returns the OOS/FINDING alias or `""` when aliasing is unsafe.
- Add `alias_id=""` parameter to `vote_for_id` and `parse_judge_vote` in `voting.py`; fall back to the alias id when the primary id yields JUDGE_ERROR.
- In `review_tally.py` `tally_code_votes`: build `ballot_id_set` from `blocks` before the item loop; compute and pass `alias_id` to each `parse_judge_vote` call.
- In `plan_review_tally.py` `_Tally`: store `ballot_id_set` on the instance after `_sorted_ids()`; pass `alias_id` in `_tally_votes_for_id`, `_votes_and_severities_for_item`, `_vote_and_severity_for_slot`, and `_write_findings_classification`.
- Add unit tests in `test_voting.py` and an integration test in `test_review_tally.py`.

### Surfaces in scope
- `python/larch/review/voting.py`
- `python/larch/review/review_tally.py`
- `python/larch/review/plan_review_tally.py`
- `python/tests/review/test_voting.py`
- `python/tests/review/test_review_tally.py`

### Open questions
- None.
