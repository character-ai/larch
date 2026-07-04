### OOS_1: [OUT_OF_SCOPE] correctness verification passed for the difficulty pipeline
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Reviewer confirms the updated difficulty pipeline looks correct overall: `trailing_plan_difficulty()` keeps trailing-only semantics, `plan_difficulty()` orders its guard and fallback logic as intended, `validate_plan_main` switches under `LARCH_REQUIRE_PLAN_DIFFICULTY=1`, `rewrite_plan_difficulty()` remains unchanged, and the regression covers the original publish-failure path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] risk-integration: python/tests/design/test_design_publish.py:617
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The publish regression finds `diff_lines` via the first `startswith` match, not the terminal trailer. Prose containing `diff_lines:` in the plan body could make ordering assertions check the wrong block. Anchor assertions on `trailing_plan_metadata_lines()` or the last trailer block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] risk-integration: python/tests/design/test_design_publish.py:327-357
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The fake plan validate path duplicates trailing parsing instead of calling the production helper, so harness regex can drift from production and weaken the regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] architecture: python/larch/design/design_step2b.py
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The drafter subprocess still does not write `design-difficulty-rating.raw.json`. The missing sidecar remains, so publish relies entirely on plan-text recovery. Write the sidecar from vendor plan text in the drafter path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

