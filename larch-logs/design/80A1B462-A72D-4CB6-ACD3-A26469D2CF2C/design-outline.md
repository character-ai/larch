## Proposed Design Outline

### Goals
- Shrink prose in `skills/shared/voting-protocol.md` and the static prose blocks of `render_voter_main` (severity floor, panel severity rubric, OOS paragraph, boilerplate directives).
- Lower the `panel-tier` skill-closure-growth ratchet token count versus the current baseline.
- Keep voting rubric semantics, OOS judging authority boundaries, and tally grammar (ballot IDs, vote-line tokens, axis names) byte-exact.

### Non-goals
- No changes to the three `VOTER_ARCHETYPES` lens blocks (validity-correctness / plan-fidelity-completeness / pragmatism-cost).
- No changes to `skills/shared/review-acceptance-rubric.md` or `skills/shared/oos-acceptance-rubric.md` content.
- No changes to voter dispatch logic, tally classification, threshold math, or panel composition.

### Approach sketch
- Density-pass `voting-protocol.md` prose paragraphs; keep tables, code fences, ballot/vote-line grammar, and file paths byte-stable.
- Trim the matching static prose strings in `render_voter_main` (`python/larch/rendering/rendering.py`), preserving parsed grammar tokens exactly.
- Propagate the shortened OOS-rubric paragraph to the two MAV parity sites (`skills/design/SKILL.md` Step 3, `skills/implement/references/step5-review-branches.md` Step 5).
- Update pinned substring assertions in `python/tests/rendering/test_rendering.py` to match new wording.
- Note baseline regen (`make regen-skill-closure-baseline`) as a post-merge implementation step.

### Surfaces in scope
- `skills/shared/voting-protocol.md`
- `python/larch/rendering/rendering.py` (`render_voter_main`)
- `skills/design/SKILL.md` (Step 3 MAV OOS paragraph)
- `skills/implement/references/step5-review-branches.md` (Step 5 MAV OOS paragraph)
- `python/tests/rendering/test_rendering.py`

### Open questions
- None.
