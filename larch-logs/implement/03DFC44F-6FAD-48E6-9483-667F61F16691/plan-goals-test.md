## Goal
Implement issue #4022: [IMPLEMENTING] [OOS] Voter progress display in design Step 3 rich header has multiple correctness gaps\n\n## Out-of-Scope Observation.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: 
**Phase**: code-review
**Vote tally**: 

## Description

Four correctness issues affect voter progress tracking in the design Step 3 rich header. Combined under Rule A (same logical concern) and Rule B (all SIMPLE < ~30 LOC).

  **Item 1 — Stale cross-round leakage (important)**: `_fresh_design_voter_manifest` freshness is only anchored to `step_start_s`, not to the current `round_dir` or round start floor. A prior round's root `plan-voter-slots.ndjson` can be treated as current, showing stale voter progress and a premature "round N complete; plan vote in progress" header during the next round's panel review.

  **Item 2 — Claude-only voter coverage gap (latent)**: When external voters are unavailable, `plan-voter-slots.ndjson` is empty (`_count_lines == 0`), so `_fresh_design_voter_manifest` returns `None` and the voter-phase header is suppressed even while Claude Voter 1 is actively running.

  **Item 3 — Premature round-complete label (latent)**: The voter branch in `_render_design_plan_review` prints "round N complete; plan vote in progress" without verifying `returned == total`. If voter manifest appears before all reviewers return, the header can show contradictory output such as `reviewers: 1/3 | voters: 0/3 returned` beside "round N complete".

  **Item 4 — Multi-round timing match failure (latent)**: Round 2+ auto-continuation timing marks may not match `_is_design_plan_review_step`, causing the renderer to fall back to generic progress output and lose voter detail for later rounds.

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*


## Test plan
(no test plan section in plan-file)
