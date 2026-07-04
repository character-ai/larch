## Proposed Design Outline

### Goals
- Lock in today's correct behavior with a regression test: a drafter-subprocess plan whose `difficulty:` trailer gets stranded mid-document by Step 5c's auto-compose must still publish cleanly (proving the #6064 side-effect fix holds).
- Close the still-latent whole-document blind-scan gap in `difficulty.py` as defense-in-depth, so `plan_difficulty()` finds a valid `difficulty:` line anywhere in the document when the trailing-span scan finds none.

### Non-goals
- Not re-implementing `_write_design_difficulty_sidecar` — it already exists in `design_postplan.py` and already covers both the drafter-subprocess and inline Step 2b paths.
- Not adding a new Step 2b hard-fail structural check for a missing sidecar — dropped per Round 1 Decision 2; it would fight the documented, deliberate "stay graceful at Step 2b, enforce at Step 5c" design.
- Not changing where `rewrite_plan_difficulty` inserts/replaces its line (stays within the trailing metadata span) — a composed document's embedded `## Plan` copy of the original trailer is expected content, not a defect to clean up.

### Approach sketch
- Add a whole-document fallback scan to `python/larch/calibration/difficulty.py`, reached only when the existing trailing-span scan (`_trailing_metadata_span`) finds no `difficulty:` line, preserving current behavior for the common case.
- Feed that fallback through both existing callers (`_splice_plan_provenance`'s `existing_difficulty` and `_resolve_publish_difficulty_rating`'s fallback in `design_publish.py`) so both benefit without call-site changes beyond the shared helper.
- Add regression coverage exercising the drafter-path + compose + publish chain (function-level, mirroring the scenario already verified empirically this session).

### Surfaces in scope
- python/larch/calibration/difficulty.py
- python/tests/calibration/test_difficulty.py
- python/tests/design/test_design_publish.py

### Open questions
- None.
