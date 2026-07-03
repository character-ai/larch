## Proposed Design Outline

### Goals
- Land the three test-coverage gaps promised in #5991's plan: `--difficulty` propagation, tier-cap/escalation cap cases, and design-panel per-tier shape checks.
- Pin the already-shipped difficulty-tier runtime (TRIVIAL/MODERATE ceiling 2, HARD ceiling 3; tier→panel mapping; escalation-gated round 3) against regression.
- Make `make test-implement-review-token-propagation`, `make test-step3-review-cap`, and `make test-dispatch-plan-review-panel` cover the plan-listed cases.

### Non-goals
- No runtime behavior changes — every changed line is test/harness code.
- No action on the 6 "non-gap" paths (already back-filled by review-fix rounds or satisfied at callers).
- No new test files; no recreation of the deleted `test-dispatch-plan-review-panel.sh` — extend the three existing successor surfaces in place.

### Approach sketch
- Gap 1: in the bash harness, add difficulty cases invoking `review-and-fix step5 --difficulty <TIER>` against the existing review-core stub, asserting captured `REVIEW_CORE_ARGV` carries `--panel simple` (TRIVIAL) / `--panel hard` (MODERATE, HARD) and `PANEL_SHAPE` stays compatible.
- Gap 2: in the cap bash harness, add HARD round-3-reachable, escalation-trigger, and Gate-C authorized-cap cases reusing the existing `plan-review run` driver + loop-stub pattern; seed tier/escalation state the way the runtime records it.
- Gap 3: in `test_plan_review_panel.py`, add per-tier `panel-dispatch` cases mirroring code-review-side `test_review_pipeline.py` tests — always Codex+Cursor pairs, TRIVIAL/MODERATE→codex `model_role=review` + ceiling 2, HARD→codex `model_role=default` + ceiling 3, escalated round→`prune_round_num=0`.

### Surfaces in scope
- `skills/implement/scripts/test-implement-review-token-propagation.sh`
- `skills/design/scripts/test-step3-review-cap.sh`
- `python/tests/review/test_plan_review_panel.py`
- Read-only anchors: `difficulty.threshold_panel_for_tier`, `plan_review_common.design_escalation_authorized`, `plan_review_loop.py`, `plan_review_panel.py`, and the `test_review_pipeline.py` mirror tests.

### Open questions
- Exact seam for passing tier/difficulty into `review-and-fix step5` and `panel-dispatch`, and how the cap harness records an escalation — resolved during drafting by reading the runtime + mirror tests. If any assertion cannot pass without a runtime edit, the assertion is wrong (test-only constraint), not the runtime.
