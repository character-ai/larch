## Proposed Design Outline

### Goals
- Cap review at 2 rounds across /implement Step 5, /review, and /design plan review.
- Front-load round 1: full paired panel, gpt-5.5 Codex specialists, no generic Codex reviewer; round 2 is a pruned backup.
- Rework pruning to evaluate at round 2 on round-1 data only, dropping quiet (no net-accepted) reviewers.

### Non-goals
- No voter, aggregator, coder, or availability-policy changes.
- No eval harness; evaluations run later against real logs.
- No re-probe round; reuse the #5255 prune-to-empty convergence path.

### Approach sketch
- Move the cap-of-5 to 2 in place across the #3662 surface list (ROUND_CAP, `--round-cap` default, round_runner fallback, review_prune round guard).
- Rewrite `review_prune.py`: prune only at round 2, require 1 round of history, retune the acceptance floor for a single-round window, fix `prune_window_evaluated` to round 2. Preserve the #5733 `-output` join fix.
- `config.py` panels: point specialist Codex `model_role` at `CODEX_DEFAULT_MODEL` (gpt-5.5); set `generic_codex_rounds` empty for both `review.panel` and `design.plan_review_panel`.
- Dynamic archetypes max and default to 1 (validation 0..1, scout filter, topology rows).
- Dispatch `--no-fallback` always; drop the per-slot reviewer fallback, the round-1-only no-fallback special case, and the spawn-everyone-on-final-round behavior.

### Surfaces in scope
- `python/larch/review/`: plan_review_common, review_and_fix, review_core_body, round_runner, review_prune, review_pipeline_shared, review_dispatch_panel, plan_review_panel.
- `python/larch/core/config.py` (panels, model roles); `python/larch/design/plan_scout.py` (scout filter max).
- `skills/shared/topology.tsv` + regenerated `docs/topology.md`.
- `python/tests/review/` plus a new round-1 ledger non-zero regression test.

### Open questions
- Concrete round-2 acceptance-floor value: propose in the plan from committed round-1 ledgers, then let plan review scrutinize.
