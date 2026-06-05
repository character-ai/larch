### OOS_1:
- **Description**: Testing section claims `--session-id` and thinned-fence assertions in router-flag recovery harness. Scenario: File only exercises `design-init-runparams.sh` (no `design-route.sh` invocation); plan work there is misleading churn
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-step0b-router-flag-recovery.sh:1-259
- **Phase**: design

### OOS_2:
- **Description**: Plan adds design-route.sh --session-id fixtures and thinned-fence assertions to the router-flag jq-merge recovery harness. Scenario: The file only exercises design-init-runparams.sh today; mixing route-driver/thin-fence coverage here expands scope beyond #3420 minimum change while test-design-structure.sh already carries the planned pin updates
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: scripts/test-step0b-router-flag-recovery.sh:1-258
- **Phase**: design

