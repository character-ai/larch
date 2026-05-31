### Resolve-conflict CI launches omit stderr-tail surfacing in _surface_ci_stderr_tail
- **Description**: Resolve-conflict CI launches omitted from `_surface_ci_stderr_tail`. Scenario: Failed `launch-*-ci.sh resolve-conflict` runs capture launcher output to `fail_file` with the same swallow pattern as the fix loop. Follow-up to #3227.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:3278-3290
- **Phase**: design
