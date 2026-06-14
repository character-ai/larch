### OOS_1:
- **Description**: close_stale_main uses bare gh issue close while close_sources_main uses _close_issue_with_retry. Scenario: Transient GitHub failures may leave fully-stale sources open with PARTIAL=true more often than consumed-source closure
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/combine_issues.py:664-673
- **Phase**: design

### OOS_2:
- **Description**: Enrichment performs one gh issue view per missing blocker. Scenario: On runs with many distinct closed blockers (the live case had 11), latency and rate-limit risk rise; fail-closed read failures still block closure
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/combine_issues.py:28-37
- **Phase**: design

