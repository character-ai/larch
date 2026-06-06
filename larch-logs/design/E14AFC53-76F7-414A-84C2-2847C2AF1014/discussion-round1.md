## Decision 1: Tier scope of the original-anchor change
- **Question**: Should "anchor the assessor verdict to plan.txt-original" apply to HARD too, or SIMPLE only?
- **Resolution**: Both tiers (unify). The assessor compares current plan vs `plan.txt-original` for HARD and SIMPLE alike — one comparison mode, no tier branches in the shared assessor scripts. HARD assessor tests get updated. Rationale: post-#3512 the loop no longer auto-revises `plan.txt`, so the legacy round-to-round comparison is largely degenerate; cumulative drift-from-original is the issue's actual target.
- **Source**: user

## Decision 2: Round-1 firing
- **Question**: On a SIMPLE run, should the assessor fire on the first/only review round, or only from round 2+?
- **Resolution**: Fire on round 1 (both tiers, per Decision 1). Relax the `ROUND_NUM < 2` skip when a `plan.txt-original` baseline exists; on round 1, use `plan.txt-original` as the comparison anchor (since no `plan-after-round-0.txt` exists). Covers the common single-round SIMPLE case — the exact #3482 gap. Safe: if nothing was applied at Gate B, current == original → TIE (no false WORSE).
- **Source**: user

## Decision 3: Auto-apply premise (round-comparison foundation)
- **Question**: Does the plan-review loop still auto-apply findings (which would make round-to-round comparison meaningful)?
- **Resolution**: No. #3512 ("stop the scope-creep ratchet — no auto-apply + drift guard", CLOSED [DONE], commit 3a602099a) removed auto-apply. `plan-review-loop.sh` is review-only and never writes `plan.txt`; `revise_status` is always `skipped`. Gate B is the sole point that revises `plan.txt`, operator-driven (Apply all / Go through each). The assessor's input therefore is: post-Gate-B `plan.txt` vs `plan.txt-original`.
- **Source**: codebase

## Decision 4: Interaction with the numeric drift guard (#3512)
- **Question**: Does anchoring the assessor to original duplicate or conflict with the #3512 drift guard?
- **Resolution**: No — complementary. The drift guard is a numeric size check (plan grew > ~2x baseline) at Step 2b.5, pre-review, on both tiers (its `drift-baseline.env` numeric seed is already tier-agnostic). The assessor is a 3-model semantic BETTER/WORSE/TIE judgment at Step 3.6, post-Gate-B. They fire at different points and measure different things; no change to the drift guard is in scope.
- **Source**: codebase

## Decision 5: Blocker dependencies — all landed
- **Question**: Are the issue's blockers (Round II refactor #3420/#3421/#3422; loop-dynamics #3512) landed, or must the design account for unlanded state?
- **Resolution**: All CLOSED [DONE]. Design against current `main` (which is ahead of the running plugin cache v47.0.72). The SIMPLE sketch-sentinel fold (#3421 Phase 6) is already in the Step 2a entry fence, so the SIMPLE `plan.txt-original` snapshot must land on the existing post-fold `design-postplan-emit.sh` path, not a colliding new fence.
- **Source**: codebase

## Decision 6: No new public flags
- **Question**: Does this need `parse-design-argv` / a new flag (issue says "as needed")?
- **Resolution**: No new public flag. The assessor runs unconditionally by tier (`design_classification` / `workflow_path` already in `run-params.json`). `parse-design-argv.sh` and the public flag surface are unchanged; "as needed" resolves to "not needed."
- **Source**: codebase

## Decision 7: Hard constraints to preserve
- **Question**: What existing behavior must not break?
- **Resolution**: Preserve (a) write-once snapshot semantics for `plan.txt-original` and `plan-after-round-<N>.txt`; (b) fail-open policy (0 effective assessors → NOT_WORSE, no spurious blocking); (c) the strict-majority WORSE tally rule and the rc=10 Continue/Stop trailer contract; (d) SIMPLE Gate-C review-round cap (3) and HARD (5) — unchanged; (e) the existing HARD WORSE Continue/Stop UX, now reused verbatim for SIMPLE.
- **Source**: codebase / issue
