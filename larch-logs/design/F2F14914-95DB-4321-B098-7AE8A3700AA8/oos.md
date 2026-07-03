### FINDING_4: Preserve the degraded fallback when render fails
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Concern**: The plan wording can be read as if a failed render should leave no `final-summary.md`, but the current helper intentionally writes a degraded fallback body on render failure. Tightening the contract the wrong way would remove a non-gating fallback and make hard failures less observable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Revise the helper spec to: unlink only clears stale pre-render files; on failure keep today's non-gating degraded-fallback behavior (or explicitly delegate to existing `render_final_summary_main` semantics without post-failure deletion).


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (latent-rerouted)

### OOS_1: [OUT_OF_SCOPE] Cancellation Final summary paths still skip design log-publish
- **Description**: [OUT_OF_SCOPE] Cancellation Final summary paths still skip design log-publish. Scenario: Plan explicitly leaves cancellation Final summary block paths untouched. Cancelled runs can still commit no run-log tree or an empty final-summary.md.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_terminal.py:788-822
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] failed-publish-tail still renders after log-publish
- **Description**: [OUT_OF_SCOPE] failed-publish-tail still renders after log-publish. Scenario: Step 5c failed-publish-tail still calls _step5c_render_final_summary after publish_core/log-publish, so committed logs can miss that outcome's enriched final-summary.md.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/design/design_step5c.py:580-583
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: Cancellation Final-summary paths still never call `design log-publish`
- **Description**: Cancellation Final-summary paths still never call `design log-publish`. Scenario: The plan explicitly defers cancellation/`failed-publish-tail` paths. Cancelled and other terminal non-Step-5c flows can still emit chat summaries without committing an enriched `final-summary.md`, leaving the same committed-log gap for those outcomes.
- **Reviewer**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_terminal.py:800
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_4: [OUT_OF_SCOPE] `failed-publish-tail` still renders only after `publish_core` without a pre-log-publish helper call
- **Description**: [OUT_OF_SCOPE] `failed-publish-tail` still renders only after `publish_core` without a pre-log-publish helper call. Scenario: The plan leaves this branch untouched, so runs that exit Step 5c with `failed-publish-tail` can still commit logs missing a pre-publish enriched `final-summary.md` (same family as the reported bug, but on a rarer tail-failure path).
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_step5c.py:580-583
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_5: [OUT_OF_SCOPE] Cancellation Final summary paths still render locally but never call `design log-publish`
- **Description**: [OUT_OF_SCOPE] Cancellation Final summary paths still render locally but never call `design log-publish`. Scenario: The plan explicitly leaves cancellation `Final summary block` paths untouched. Cancelled runs can still emit chat summary without a committed run-log tree containing `final-summary.md`, leaving a completeness gap relative to the plan goal but outside the binding terminal-report bug
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_terminal.py:788-811
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

