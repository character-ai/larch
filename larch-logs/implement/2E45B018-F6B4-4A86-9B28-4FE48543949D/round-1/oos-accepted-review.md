### OOS_1: correctness: skills/design/scripts/review-design-step3-loop.sh:638-656
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [blocking] Embedded Step 3 loop still collapses pre-dispatch round-body failures to panel-failed with a completed round. run_step3_round_body creates plan-review/round-1 then fails before launching reviewers; wrapper preserves panel-failed and design can continue with zero reviewer coverage. Add a dispatch-complete marker and emit panel-init-failed before any reviewer launch; include it in loop allowlists and evidence recording.
- **Suggested revision**: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] **Pre-existing:** `skills/design/SKILL.md` documents a hard stop when `feature-description.txt` is missing before Step 2b, but `skills/design/scripts/design-step0-init.sh:125-134` only best-effort writes the file; there is no mechanical abort if it remains empty after `already-planned` routing. That gap predates this branch’s provenance work.
- **Reviewer**: dyn-regression-surface-output.txt
- **Concern**: - **Pre-existing:** `skills/design/SKILL.md` documents a hard stop when `feature-description.txt` is missing before Step 2b, but `skills/design/scripts/design-step0-init.sh:125-134` only best-effort writes the file; there is no mechanical abort if it remains empty after `already-planned` routing. That gap predates this branch’s provenance work.
- **Suggested revision**: Address the concern above.


### OOS_3: correctness: python/plan_quality.py:519-520
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Numeric mechanical_churn normalization treats 0 as true mechanical_churn: 0 incorrectly enables mechanical-churn advisory and may alter Step 2b.5 gating Normalize only positive integers to true; treat 0 as false or invalid
- **Suggested revision**: Address the concern above.


