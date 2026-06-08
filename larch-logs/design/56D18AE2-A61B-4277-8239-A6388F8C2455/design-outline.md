## Proposed Design Outline

### Goals
- Cut wasted review tokens: from round 3, skip tool×archetype combos with zero accepted findings in their last 2 launched rounds.
- Cover all three review surfaces: `/design` plan review, `/implement` Step 5 code review, `/review` diff mode.
- Round 5 (the cap) always re-probes with the full panel; rounds 1-2 always run full.

### Non-goals
- No review-round-cap edits — #3662 landed the flat cap of 5; this builds on it.
- No pruning for `/review` description mode (single-pass) or for rounds 1-2.
- No cross-run memory — the prune ledger is per-run only.

### Approach sketch
- Refresh the prior reviewed plan: one shared helper `scripts/reviewer-prune.sh` with `record` (post-tally ledger rows per launched slot) and `filter` (pre-launch manifest rewrite) subcommands.
- Hook `filter` at the single point in each dispatcher where the slot manifest is complete; the filtered manifest becomes authoritative for everything downstream.
- Launched rounds are strike rounds; "accepted" = voted-in rows in the round's findings-classification TSV, attributed by exact normalized token match.
- Pruned-empty rounds advance the round counter (`prune-skipped`), never converge or count as degraded.
- `LARCH_REVIEWER_PRUNE=off` kill switch; fail open on missing/corrupt ledger.

### Surfaces in scope
- `scripts/reviewer-prune.sh` (new, + contract md + offline harness + Makefile target).
- `skills/review/scripts/` — `dispatch-panel.sh`, `review-core.sh` (+ md, tests).
- `skills/review-and-fix/scripts/` — `review-and-fix.sh`, `review-implement-step5-loop.sh` (+ md, tests).
- `skills/design/scripts/` — `run-step3-review.sh`, `dispatch-plan-review-panel.sh`, `plan-review-loop.sh` (+ md, tests); `scripts/lib-design-round-artifacts.sh`.
- Prose/docs: `skills/review/SKILL.md`, `skills/review/references/heavy-worker.md`, `skills/design/SKILL.md`, `skills/implement/SKILL.md`, `skills/design/references/plan-review.md`, `docs/configuration-and-permissions.md`, `docs/point-competition.md`, `docs/linting.md`.

### Open questions
- None.
