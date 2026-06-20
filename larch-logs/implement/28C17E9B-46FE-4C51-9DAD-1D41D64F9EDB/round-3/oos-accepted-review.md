### OOS_10: correctness: python/plan_review.py:1274-1376
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Multi-round Step 3 clears degraded_values on continuation without persisting INVALID_SLOT_PANEL_WARNING. Round 1 drops invalid slot rows and sets INVALID_SLOT_PANEL_WARNING; operator applies findings and continues to round 2; degraded_values is reset so the final complete envelope omits the degradation. Persist warning keys to .step3-review-result.env before clearing carry state, or merge carry keys across round boundaries.
- **Suggested revision**: Address the concern above.


### OOS_11: risk-integration: python/plan_review.py:1358-1376
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Multi-round Step 3 continuation clears INVALID_SLOT_PANEL_WARNING carry state. Round 1 degrades on invalid slot rows and sets INVALID_SLOT_PANEL_WARNING; operator continues to round 2; final Step 3 stdout omits the warning because degraded_values is reset and .step3-review-result.env is unlinked on continue. Preserve _STEP3_ROUND_CARRY_KEYS across PLAN_REVIEW_CONTINUE or merge warnings into complete_values at final envelope emit.
- **Suggested revision**: Address the concern above.


### OOS_12: **risk-integration** `python/plan_review.py:1358-1376` — On auto-continuation (`PLAN_REVIEW_CONTINUE=true`), the loop unlinks `.step3-review-result.env` and resets `degraded_values`, dropping any prior-round `INVALID_SLOT_PANEL_WARNING` / `DEGRADED_PANEL_WARNING` without archiving them elsewhere. `MERGE_KEYS` only helps within a single round’s persist cycle; it cannot recover warnings after the env file is deleted. A round-1 panel that dropped invalid slots but continued with remaining reviewers will lose that warning if the operator continues to round 2, even though round 1 ran a partial panel on an unreviewed manifest shape. **Suggested fix:** Before unlinking the result env on continuation, merge `_STEP3_ROUND_CARRY_KEYS` into a durable sidecar (for example `plan-review-degradation-warnings.md` or cumulative keys in the result env that are re-loaded at the next round entry), or carry warnings forward in `degraded_values` across continuation instead of resetting to `{}`.
- **Reviewer**: dyn-step3-propagation-output.txt
- **Concern**: - **risk-integration** `python/plan_review.py:1358-1376` — On auto-continuation (`PLAN_REVIEW_CONTINUE=true`), the loop unlinks `.step3-review-result.env` and resets `degraded_values`, dropping any prior-round `INVALID_SLOT_PANEL_WARNING` / `DEGRADED_PANEL_WARNING` without archiving them elsewhere. `MERGE_KEYS` only helps within a single round’s persist cycle; it cannot recover warnings after the env file is deleted. A round-1 panel that dropped invalid slots but continued with remaining reviewers will lose that warning if the operator continues to round 2, even though round 1 ran a partial panel on an unreviewed manifest shape. **Suggested fix:** Before unlinking the result env on continuation, merge `_STEP3_ROUND_CARRY_KEYS` into a durable sidecar (for example `plan-review-degradation-warnings.md` or cumulative keys in the result env that are re-loaded at the next round entry), or carry warnings forward in `degraded_values` across continuation instead of resetting to `{}`.
- **Suggested revision**: Address the concern above.


