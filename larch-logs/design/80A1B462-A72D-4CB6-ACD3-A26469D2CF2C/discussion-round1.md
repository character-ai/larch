## Decision 1: Include the Python runtime voter-prompt renderer in scope
- **Question**: Should compression include the Python-rendered runtime voter prompt (`render_voter_main` in `python/larch/rendering/rendering.py`), not just the markdown doc?
- **Resolution**: Yes. Compress both `skills/shared/voting-protocol.md` and the static prose blocks in `render_voter_main` (severity floor, panel severity rubric, OOS paragraph, boilerplate directives). Do not touch the dynamically-loaded `skills/shared/review-acceptance-rubric.md` content or its own prose. Update pinned substring assertions in `python/tests/rendering/test_rendering.py` to match.
- **Source**: user

## Decision 2: Leave VOTER_ARCHETYPES lens blocks untouched
- **Question**: Should the three `VOTER_ARCHETYPES` lens blocks (validity-correctness / plan-fidelity-completeness / pragmatism-cost) in `rendering.py` also get a compression pass?
- **Resolution**: No. Leave them as-is; they are dense, behavior-critical per-lens instructions with pinned test assertions, and the regression risk outweighs the marginal token savings.
- **Source**: user

## Decision 3: Sync the OOS-rubric paragraph across all 4 documented parity sites
- **Question**: The repo keeps an OOS-rubric paragraph in near-verbatim parity across 4 sites (`voting-protocol.md`, `rendering.py`, `skills/design/SKILL.md` Step 3 MAV, `skills/implement/references/step5-review-branches.md` Step 5 MAV) per an explicit maintenance comment. If that paragraph's wording shrinks, should all 4 sites be kept in sync?
- **Resolution**: Yes. If the OOS paragraph wording changes, propagate the same shortened wording to all 4 sites, including the two MAV paraphrase sites outside the issue's named scope, to preserve the documented parity invariant.
- **Source**: user
