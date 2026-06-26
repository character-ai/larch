### OOS_1: [OUT_OF_SCOPE] Removed scoreboard separation sentence in `docs/point-competition.md`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The diff removed the scoreboard separation sentence the plan did not authorize removing. Readers may conflate pruning net math with competition scoreboard weighting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restore: Competition scoreboards and Top reviewers use weighted points separately.

### OOS_2: [OUT_OF_SCOPE] `/design` plan-review pruning window vs global docs contract
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `docs/point-competition.md` describes rounds 2–4 globally, but `/design` still skips pruning outside rounds 3–4 in `python/plan_review_panel.py` (`if prune_round_num not in {3, 4}`). Operators validating `/design` from this doc will expect round-2 pruning that does not run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Scope the rounds 2–4 wording to `/implement` (and `/review` multi-round paths), or widen `plan_review_panel._filter_pruned` to match the shared pipeline.
  - From cursor-specialist-testing-output.txt: Either scope the doc wording to `/implement` and `/review`, or extend the design gate to round 2 if that is intended.

### OOS_3: [OUT_OF_SCOPE] Stale operator-facing prose still says pruning is rounds 3–4 only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-prune-window-output.txt
- **Severity**: important
- **Concern**: Step 5 banners, `skills/implement/SKILL.md`, `skills/implement/scripts/step-5-review.sh`, and `docs/configuration-and-permissions.md` still describe rounds 1–2 as unpruned and/or pruning in rounds 3–4 only, while `/implement` Step 5 now prunes in round 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Update banner prose to “rounds 2-4” (and note round-2 single-row evidence if helpful).
  - From cursor-specialist-testing-output.txt: Align env-var docs and Step 5 banners with rounds 2-4 and the round-aware evidence rule.
  - From dyn-dyn-prune-window-output.txt: Operator-facing Step 5 banners still say “rounds 3-4” for mechanical pruning; runtime behavior for round 2 now differs from what those strings advertise.

### OOS_4: [OUT_OF_SCOPE] No end-to-end `review core` round-2 pruning integration test
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Filter-level tests cover round-2 pruning logic, but there is no parallel integration test that round-2 dispatch actually prunes when `prune_window_evaluated(2)=="true"`. Future `prune_evaluated` / filter drift would not be caught at the dispatch boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add a `review core` round-2 case asserting `PRUNE_ACTIVE=true` and non-zero `PRUNED_COUNT` when round-1 ledger is zero-yield.

### OOS_5: [OUT_OF_SCOPE] Optional round-3 guard test does not model a literal round-2 launch gap
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test_reviewer_prune_filter_round_three_requires_two_recent_rounds` seeds only round 1 via `_record_prune_rounds`, which matches the effective ledger when round 2 never recorded, but does not construct a ledger with a literal round-2 launch gap after round 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional hardening only; current coverage already blocks the `min_recent` regression the plan cares about.

