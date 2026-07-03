### OOS_1: [OUT_OF_SCOPE] Clarify mode source mismatch
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: Clarify's mode source differs from log-publish's mode resolver, so the tracking comment can disagree with the committed summary when mode is only present in run params or source env.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Reuse _resolve_summary_mode or add MODE to CLARIFY_ENV_ALLOW.

### OOS_2: [OUT_OF_SCOPE] Deferred outcomes still skip the centralized pre-copy render
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-summary-publish
- **Severity**: latent
- **Concern**: Cancellation/final-summary-block and failed-publish-tail outcomes still skip the centralized pre-copy render, leaving those outcomes with no committed enriched summary as a pre-existing scope gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address in follow-up if those outcomes need committed enriched summaries.
  - From dyn-dyn-summary-publish: Cancellation `Final summary block` paths and `failed-publish-tail` still never get a pre-copy render through `design log-publish`; the plan explicitly defers those paths, so committed logs can remain empty for those outcomes (pre-existing scope gap, not amplified by this diff).

### OOS_3: [OUT_OF_SCOPE] Dry-run cannot validate render-before-copy ordering
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: Dry-run skips the pre-copy render path, so it cannot catch regressions in render-before-copy ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Optional dry-run hook or doc note if operators rely on dry-run for validation.

### OOS_4: [OUT_OF_SCOPE] Label-remove failure test needs a real session
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The label-remove failure test never exercises failed-clarify on a real session because it uses an empty `SESSION_ID`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add label-remove failure test with non-empty SESSION_ID asserting failed-clarify reaches log-publish before summary upsert.

### OOS_5: [OUT_OF_SCOPE] Final-summary fallback body predates this branch
- **Reviewer(s)**: dyn-dyn-summary-publish
- **Severity**: latent
- **Concern**: `render_final_summary_main` can still succeed with a degraded fallback body when render fails but post-enrichment succeeds; that behavior predates this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-summary-publish: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Existing push test does not assert enriched summary content
- **Reviewer(s)**: dyn-dyn-summary-publish
- **Severity**: latent
- **Concern**: The pushed-tree log-publish test only checks existence, not enriched summary content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-summary-publish: Address the concern above.

