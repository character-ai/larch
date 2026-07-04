## Proposed Design Outline

### Goals
- Stop `_summarize` from advancing absent targets to 0 during gap revisions.
- Preserve `end=0` for permanently removed targets by advancing post-loop.
- Add a `--since-tag` + gap + reappear test to prevent regression.

### Non-goals
- No change to `_build_revisions` or detailed ledger output.
- No new CLI flags or public API surface.
- No change to the reappear-detection and accumulator-reset logic added in #6219.

### Approach sketch
- In `_summarize`, skip the advance call for any target absent from `snapshot_values` in the current revision.
- After the revision loop, identify accumulators whose target is absent from the final snapshot and advance them to 0 (permanent removal).
- Add `test_since_tag_summary_with_gap_and_reappear` using the existing `_fixture_history_with_panel_tier_gap` helper.

### Surfaces in scope
- `python/larch/lint/skill_closure_ledger.py` (`_summarize`)
- `python/tests/lint/test_skill_closure_ledger.py` (new test)

### Open questions
- None.
