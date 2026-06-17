### OOS_1:
- **Description**: The plan updates stall-recovery-report.sh retry_cap_for but not the sibling stall-recovery-report.md table that still documents ci-fix-exhausted max attempts as 8.. Scenario: Operators reading the .md contract get stale retry guidance after Python/bash classifiers move ci-fix-exhausted to cap 0.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/stall-recovery-report.md:201
- **Phase**: design
