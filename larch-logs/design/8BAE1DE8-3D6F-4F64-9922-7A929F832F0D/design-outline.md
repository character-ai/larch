## Proposed Design Outline

### Goals
- When per-item under-quorum is the only degraded cause, re-vote only the affected items instead of retrying the full panel.
- Avoid re-running reviewers and the aggregator when they produced healthy output.
- Keep all other degraded retry paths, the retry cap, and attempt-1 tally preservation unchanged.

### Non-goals
- No changes to the `/design` plan-review pipeline (`plan_review_round.py` unaffected).
- No changes to the voter dispatch or tally core logic (quorum threshold, JUDGE_ERROR removal rate).
- No changes to the panel shape, retry cap count, or per-slot diagnostic recording.

### Approach sketch
- In `_run_round` (`round_runner.py`), after the first `review_core_capture`, detect pure under-quorum: `UNDER_QUORUM_COUNT > 0`, `PARSE_FAILED_COUNT == 0` (from core env), and `FAILED_SLOTS == 0` (from `threshold_env`).
- Filter the round's `findings.md` to only the under-quorum item IDs; dispatch voters on the filtered ballot; merge new voter file content with original voter files; re-tally with the merged voter content.
- Use the same `degraded-retry.flag` / `degraded-retry.done` sentinels and attempt-1 tally copy (`voting-tally-degraded-attempt-1.md`) for the re-vote path.
- Add a parametrized test in `test_review_and_fix.py` using the existing `review_core_impl` stub to verify re-vote-only vs. full-retry dispatch.

### Surfaces in scope
- `python/larch/review/round_runner.py`
- `python/tests/review/test_review_and_fix.py`

### Open questions
- None.
