### OOS_1:
- **Description**: Plan does not run `python/cli.py oos disposition-checkpoint` after post-ship `oos file`. Scenario: Bash path still uses the checkpoint to validate terminal disposition (inline-triage breadcrumbs, rejected markers); Python path may mark runs complete without that cross-check
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/references/oos-pipeline.md:57-58
- **Phase**: design

