## Proposed Design Outline

### Goals
- Consume child-1's difficulty `applied_tier` to compose **tiered reviewer panels** (TRIVIAL/MODERATE/HARD) with per-tier round ceilings **2/2/3** across /implement Step 5, /review, and /design plan review.
- Add tier-aware **escalation** (reuse `_step5_post_round_gates` for /implement+/review; ≥2 high-sev accepted for /design), **1:30 random HARD audits**, and a `--difficulty` operator override — all logged into the existing `difficulty-rating.json` fields.
- Keep the procedure identical at every tier: only reviewer composition, reviewer model, and ceiling vary.

### Non-goals
- No #5992 difficulty-calibration analyzer work.
- No change to voting (#5887), aggregation, fix-coder (#5888), or the rating-capture rubric/schema (#5990).
- No /design vendor shedding (design always keeps Codex+Cursor pairs).

### Approach sketch
- Add a shared **tier→panel resolver** (frozen dataclass) in `calibration/difficulty.py`, plus `resolve_applied_tier(rating, floors, override, audit)`; keep tier ceilings, per-tier model roles, and the audit ratio (30) as `config.py` Finals.
- Wire the resolver into `review_dispatch_panel.py` (/implement Step 5 + /review) and `plan_review_panel.py` (/design): pick model_role (gpt-5.4-mini vs gpt-5.5), singles-vs-pairs + flip-on-vendor-down (TRIVIAL only), and replace uniform round-cap 2 with the tier ceiling.
- Escalation in `review_and_fix.py` / `round_runner.py` (existing gate) and `plan_review_loop.py` (new ≥2-high-sev design trigger): escalated round runs next tier's full panel, precedes pruning, no prune that round.
- Round-3 branch (HARD only): generalize the prune window (round 3 prunes on rounds 1-2 data) while preserving the #5733 `-output` label-join fix; add its regression test.
- Add `--difficulty` argv to /implement, /review, /design; inject an RNG seam for the audit so it is testable.

### Surfaces in scope
- `python/larch/calibration/difficulty.py`, `python/larch/core/config.py`
- `python/larch/review/`: `review_dispatch_panel.py`, `plan_review_panel.py`, `review_and_fix.py`, `round_runner.py`, `plan_review.py` / `plan_review_loop.py`, `review_prune.py` / `review_pipeline_shared.py`
- `--difficulty` argv surfaces in /implement, /review, /design (skills + python argv parsers)
- Tests: `test_difficulty.py`, `test_review_and_fix.py`, panel tests, + #5733 prune-ledger regression test

### Open questions
- None. (Escalation trigger, no-rating fallback, and audit-vs-override precedence resolved in Round 1.)
