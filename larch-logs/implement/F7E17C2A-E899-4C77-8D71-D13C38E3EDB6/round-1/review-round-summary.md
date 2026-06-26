# Review Round 1

- Mode: `diff`
- 1 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: `/design` plan-review pruning window vs global docs contract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-generalist-output.txt, dyn-dyn-prune-window-output.txt
- **Severity**: important
- **Concern**: `docs/point-competition.md` now describes conditional spawning as active in rounds 2–4 immediately after **Where Scoring Applies** lists `/design`, but `python/plan_review_panel.py` `_filter_pruned` still returns the unpruned manifest unless `prune_round_num` is 3 or 4. `/implement` and `/review` can prune in round 2 via the shared `review_pipeline` window, while `/design` round 2 never reaches `reviewer_prune_filter`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Either allow round 2 in plan_review_panel._filter_pruned or scope the docs to /implement and /review and document /design as rounds 3-4 only.
  - From codex-generalist-output.txt: Route `_filter_pruned` through `review_pipeline.prune_window_evaluated()` or include round 2 in this guard, then add a plan-review panel test for round-2 pruning.
  - From dyn-dyn-prune-window-output.txt: Either extend `python/plan_review_panel.py:357-359` to `{2, 3, 4}` so `/design` matches the shared filter window, or narrow `docs/point-competition.md:123-125` (and the `LARCH_UNIQUE_FINDER_BONUS` paragraph if needed) to `/implement` Step 5 and other code-review paths that call `review dispatch-panel`, leaving `/design` at rounds 3-4.


