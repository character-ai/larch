## Proposed Design Outline

### Goals
- Rewrite `design.plan_voters` to the `review.voters` shape: three codex-primary voters (validity, plan-fidelity, pragmatism), each waterfalling codex then cursor then claude, with a single-Claude floor when both externals are down.
- Add a per-archetype HARD model override so only top-yield Codex archetypes run gpt-5.5; every other static row and all dynamics stay gpt-5.4-mini.
- Land exactly 2 gpt-5.5 reviewer rows per round per skill at HARD, with no archetype at both models.

### Non-goals
- No change to TRIVIAL or MODERATE panels, except dropping dyn-codex at TRIVIAL code review.
- No change to round cap, `--no-fallback` drop semantics, aggregators, scout waterfall, or `/implement` and `/review` voters.
- No voter-drift escalation now; that stays a future `/voter-calibration`-watched guard.

### Approach sketch
- config.py: replace the `design.plan_voters` policy rows with codex-primary `VoterPolicyDefault` rows mirroring `review.voters`.
- config.py: add a `(panel, archetype) -> role` HARD-override map next to `DIFFICULTY_CODEX_MODEL_ROLES`; plan review picks pragmatic + requirements, code review picks correctness + edge-cases.
- Consume the override in `plan_review_panel._static_slot_rows` and `review_dispatch_panel._append_static_specialist_rows`; pin codex dynamic rows to the review role at every tier.
- review_dispatch_panel: drop dyn-codex at TRIVIAL, keep dyn-cursor; design keeps its dynamic pair at all tiers.
- Update `docs/review-agents.md`, `docs/external-reviewers.md`, `docs/voting-process.md`, `docs/configuration-and-permissions.md`, and `skills/shared/topology.tsv` in lockstep; teach `/voter-calibration` the design voter labels.

### Surfaces in scope
- `python/larch/core/config.py`, `python/larch/calibration/difficulty.py`
- `python/larch/review/plan_review_panel.py`, `python/larch/review/review_dispatch_panel.py`, voter-calibration label parsing
- panel/dispatch/voter tests; `docs/*` and `skills/shared/topology.tsv` projections

### Open questions
- None.
