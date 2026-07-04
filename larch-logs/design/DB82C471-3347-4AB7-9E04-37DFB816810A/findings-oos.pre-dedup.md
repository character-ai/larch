### OOS_1: /design still runs --structured-reviewer-validation after substantive validation
- **Description**: /design still runs --structured-reviewer-validation after substantive validation. Scenario: /implement Step 5 uses validation-mode only, but /design plan review also passes --structured-reviewer-validation. Prose no-findings without JSON or NO_ISSUES_FOUND can still be demoted NOT_SUBSTANTIVE on the structured path even after this fix.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/review/plan_review_round.py:865-867
- **Phase**: design



