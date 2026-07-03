### OOS_1: [OUT_OF_SCOPE] Cancellation and failed-publish-tail still bypass log-publish
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-summary-publish
- **Severity**: latent
- **Concern**: Cancellation and `failed-publish-tail` terminal paths still never call `design log-publish`, so those rare outcomes can still miss an enriched committed `final-summary.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-summary-publish: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Clarify follow-up can hide a failed summary upsert
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: `clarify.py` still discards `_render_clarify_final_summary`’s return value, so a failed tracking-comment upsert after a successful log-publish can stay silent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Double-render paths can diverge or leave the tracking comment stale
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-summary-publish
- **Severity**: latent
- **Concern**: The clarify/approved publish flow renders the summary twice, so a failed second pass or enrichment drift can leave the committed log and tracking comment inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-summary-publish: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Clarify label-remove failure path lacks coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: There is still no test for the session-backed label-remove failure path with a failed-clarify outcome and upsert gating, so that combination could regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add clarify test with SESSION_ID, label-remove failure, failed publish, and outcome/order assertions.

### OOS_5: [OUT_OF_SCOPE] Shared mode resolver is duplicated between clarify and log-publish
- **Reviewer(s)**: dyn-dyn-summary-publish
- **Severity**: nit
- **Concern**: `_resolve_summary_mode` is duplicated in `clarify.py` and `design_log_publish_flow.py`, so future edits could reintroduce mode drift between the committed log and the tracking comment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-summary-publish: Address the concern above.

