## Proposed Design Outline

### Goals
- Treat NOT_SUBSTANTIVE as coverage-satisfied for the archetype coverage gate when all reviewers in that archetype returned NOT_SUBSTANTIVE.
- Clear a stale stall result env before starting a fresh review on step5-review recovery so retries make progress.

### Non-goals
- Do not change the threshold gate (NOT_SUBSTANTIVE stays "failed" for the >50% slot-failure check).
- Do not change MAV, main-agent-vote, or other stall branches.
- Do not add new flags, tiers, or per-tier carve-outs; the fix applies to any panel tier/shape.

### Approach sketch
- In `_static_coverage_reason` (`review_core_body.py`): add NOT_SUBSTANTIVE to the set of statuses that mark a slug as "covered" for the archetype coverage gate (without adding it to `collector_success`, which is used only for tool-absent excusal).
- In `step-5-review.sh`: remove `stall` from the "return cached result" branch; merge it into the "stale → clear and restart" branch instead.
- Update `test-step-5-review.sh`: the existing "stall result is reused" test must become a "stall result triggers fresh start" test.
- Add a Python unit test for `_static_coverage_reason` with an all-NOT_SUBSTANTIVE archetype.

### Surfaces in scope
- `python/larch/review/review_core_body.py`
- `python/tests/review/test_review_pipeline.py`
- `skills/implement/scripts/step-5-review.sh`
- `skills/implement/scripts/test-step-5-review.sh`
- `skills/implement/scripts/test-step-5-review.md`

### Open questions
- None.
