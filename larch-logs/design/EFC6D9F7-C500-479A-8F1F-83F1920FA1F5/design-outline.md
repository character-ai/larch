## Proposed Design Outline

### Goals
- Count dynamic reviewers identically to static in `INTENDED_SLOTS` / `SUCCEEDED_SLOTS` / `FAILED_SLOTS` / `COUNTED_SLOTS`.
- Surface dynamic reviewer failures and straggler-drops as warnings in the run summary (`Reviewer slot failures` / `Warnings`).
- Preserve dropped/straggler per-reviewer stderr/sidecars into the committed run log bundle before session teardown.

### Non-goals
- Changing the reviewer failure threshold percentage or formula.
- Modifying scout archetype selection or how dynamic slots are launched.
- Changing straggler adaptive cutoff timing.
- Retroactive fixes to already-committed run logs.

### Approach sketch
- Remove static-only guards from `check_reviewer_failure_threshold`, `_straggler_excused_static_slugs`, `_static_slug_for_file`, and related helpers in `python/review_pipeline.py`.
- Extend dropped-slot accounting and the slug mapper to handle `dyn-*` basenames.
- Ensure `agent_waterfall.py` straggler-drop emission produces the same downstream warning path for dynamic slots as it does for static slots.
- Copy straggler-dropped reviewer stderr/sidecars into the per-round log directory before Step 18 teardown so they appear in committed larch-logs/.
- Add tests in `python/test_review_pipeline.py` covering dynamic-reviewer failure counting, straggler-drop accounting, and warning surfacing.

### Surfaces in scope
- `python/review_pipeline.py` — threshold/accounting/slug-mapper functions
- `python/agent_waterfall.py` — straggler-drop emission and sidecar handling
- `python/test_review_pipeline.py` — test coverage
- Run-summary renderer — warning/failure count for dynamic drops

### Open questions
- None.
