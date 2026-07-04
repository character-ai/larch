## Proposed Design Outline

### Goals
- Compress the static, machine-non-parsed prose in the design plan-review reviewer prompt builder so per-slot scaffold bytes drop measurably.
- Preserve every machine-parsed grammar element and payload-inclusion path byte-for-byte.

### Non-goals
- No changes to `render_voter_main`, `_oos_proposal_instruction`, `_architectural_guidelines_review_section`, or any implement-side/aggregator builder (owned by sibling issues #6160/#6161).
- No new CI ratchet/governance mechanism (owned by #6156/#6165) and no panel-topology, dispatch, or archetype-count changes.

### Approach sketch
- Rewrite the fixed procedural body of `render_plan_review_main` (TSV-contract/sentinel instructions, plan-directive prose, tier-emphasis line) in `python/larch/rendering/rendering.py`, tightening wording while keeping every tested substring (TSV header/columns, JSON sentinel, `[OUT_OF_SCOPE]`/`[SCOPE-REDUCTION]`/`[ALREADY_ADDRESSED]`, scope-anchor heading) byte-identical.
- Tighten the four `_PLAN_REVIEW_ROLES` archetype blurbs, preserving each archetype's distinct emphasis.
- Tighten `_GENERIC_CODEX_PLAN_REVIEW_ROLE` in `python/larch/review/plan_review_panel.py`; leave the already-tested one-line `_slot_row` fallback untouched (covered by four exact-match tests, negligible savings potential).
- Update the small number of existing tests that assert exact prose substrings (not grammar) to match new wording, without weakening what they verify.

### Surfaces in scope
- `python/larch/rendering/rendering.py` (`render_plan_review_main` and its exclusive helpers)
- `python/larch/review/plan_review_panel.py` (`_GENERIC_CODEX_PLAN_REVIEW_ROLE`)
- `python/tests/rendering/test_rendering.py` (prose-substring assertions only)

### Open questions
- None.
