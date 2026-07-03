### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_step5c.py:555-569; python/larch/design/design_publish.py:992-1008
- **Concern**: [SCOPE-REDUCTION] The step5c retry plan can re-run log-publish after publish_core already attempted it.. Scenario: When approved publish reaches _run_log_publish_after_capture and returns rc 5, step5c enters the planned failed-publish-tail branch even though design log-publish already ran. The planned retry with outcome failed-publish-tail can create a second log-publish attempt for the same run id, violating the plan's no-double-publish scope.
- **Proposed resolution**: Narrow the step5c centralized retry to catastrophic exits with no prior log-publish evidence. If publish stdout or result env already contains PUBLISH_OK, PR_URL, or RECOVERY_BRANCH from design log-publish, skip the centralized retry and keep the local-render fallback.
