### OOS_1: [OUT_OF_SCOPE] Merged postplan-emit --with-plan-size still returns on check-size failure without execution-issues self-log
- **Description**: [OUT_OF_SCOPE] Merged postplan-emit --with-plan-size still returns on check-size failure without execution-issues self-log. Scenario: Initial Step 2b and Gate B merged re-emits call plan check-size inside design_postplan.py, not design step2b5; failures return rc=1 with no append-failure, so the new self-logging pattern does not cover the busiest path
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/design_postplan.py:236-238
- **Phase**: design
