# Review Round 1

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: `python/larch/review/plan_review_loop.py` duplicate convergence reason overlay
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-testing, dyn-dyn-cap-policy
- **Severity**: important
- **Concern**: The duplicate-convergence overlay can replace a terminal `PLAN_REVIEW_CONTINUE_REASON` with `converged-no-new-findings` even when a stopped review should preserve a cap boundary or protected approval reason. That makes the machine-readable continuation signal wrong for round-2 cap-reached cases and for `--per-round-approval` flows that need `explicit-approve`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Restore the old `reason == "small-clean"` guard, or otherwise skip this override when `review_count >= cap`, and change the round-2 test expectation back to `cap-reached`.
  - From cursor-specialist-testing: Restore narrow guard for explicit-approve or add continuation test for approve_requested=true with duplicates at round 2
  - From dyn-dyn-cap-policy: Keep the broader convergence rewrite for cap/convergence paths, but exclude protected reasons such as `explicit-approve` (and `converged-pruned-empty`) from the final overlay; add a round-2 `--approve-requested true` duplicate re-raise test.


### FINDING_2: `python/larch/report/progress_report.py` stale round_cap is not clamped in emitted metadata
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-cap-policy
- **Severity**: important
- **Concern**: `progress_report` can persist a legacy `round_cap: 3` from `difficulty-rating.json` into `round-meta.json` without clamping it to the current tier ceiling, so resolved artifacts can still advertise `ceiling_in_effect: 3` / `round_cap: 3` even though runtime enforcement now caps at 2. The same path also lacks coverage for that stale-cap regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Clamp with min(stored tier_ceiling(panel_tier)) or resolve via shared difficulty helper before emitting metadata
  - From cursor-specialist-testing: Clamp via min(stored_cap tier_ceiling(panel_tier)) or resolve_panel_tier; add test seeding round_cap 3 expecting ceiling_in_effect 2
  - From dyn-dyn-cap-policy: Resolve cap the same way as _resolution_from_data (or call resolve_panel_tier) before writing ceiling_in_effect and round_cap; add a regression test with a stale round_cap: 3 fixture asserting emitted meta is 2.


### FINDING_4: `skills/review/SKILL.md` final-round `/review` handling should apply accepted findings before stopping
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Standalone `/review` now treats cap-reached final rounds as if another review should not happen, but it can stop without applying accepted findings first, so HARD round 2 exits before the intended fixes land.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Apply accepted findings for cap-reached final rounds, then stop without scheduling another review round.


