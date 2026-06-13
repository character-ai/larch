### OOS_1:
- **Description**: CI unquoted focus-area anchor currently lives in a comment inside dispatch-panel.sh. Scenario: Deleting dispatch-panel.sh removes the literal code-quality / risk-integration / correctness / architecture / security anchor unless duplicated in the Python prompt-owning surface
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/scripts/dispatch-panel.sh:123
- **Phase**: design

### OOS_1:
- **Description**: Stale review-core.sh reference in Step 5 launcher contract doc not named in the plan explicit file list. Scenario: Grep sweep or implementer may miss this contract doc; operators see obsolete panel-selection prose
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: scripts/run-step5-review.md:10
- **Phase**: design

