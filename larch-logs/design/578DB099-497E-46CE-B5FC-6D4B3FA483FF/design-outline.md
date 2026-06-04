## Proposed Design Outline

### Goals
- Collapse the `/review` code-review panel from 6 static archetypes to 4: `security`, `correctness`, `edge-cases` (folds `structure`), `testing` (folds `plan-fidelity`).
- Run both vendors on every slot: each of the 4 static archetypes and each scouted dynamic archetype emits a Cursor slot and a Codex slot (gated on availability).
- Keep the 4-archetype attribution stable so the deferred #3463 pruner can key on it.

### Non-goals
- No #3463 conditional spawning or pruning — this run hits harder upfront; #3463 prunes later.
- No changes to `/design` plan review (`run-step3-review.sh`, `dispatch-plan-review-panel.sh`).
- No run-log re-mining; catch-rate validation is a separate follow-up.

### Approach sketch
- In `dispatch-panel.sh`: shrink `cursor_specialists` to the 4 slugs; emit a Codex static twin per archetype; emit Codex dynamic twins; replace forced `codex_present_for_waterfall="false"` with `CODEX_AVAILABLE`.
- Fold `structure` into the `edge-cases` prompt and `plan-fidelity` into the `testing` prompt as a "secondary scan, flag only critical" lens (existing `reviewer-templates.md` pattern); regenerate affected `agents/*.md`.
- Update the reserved-slug list in both `dispatch-panel.sh` and `scout-dynamic-archetypes.sh` to the new 4 slugs.
- Narrow `tally-code-votes.sh` focus-area map + attribution to the 4 slugs; confirm `codex-specialist-*` slot parsing covers Codex static twins.

### Surfaces in scope
- `skills/review/scripts/dispatch-panel.sh`, `scripts/scout-dynamic-archetypes.sh`
- `skills/shared/reviewer-templates.md`, regenerated `agents/reviewer-*.md`
- `skills/review/scripts/tally-code-votes.sh`
- `docs/review-agents.md` and prose referencing the 6 archetypes

### Open questions
- None.
