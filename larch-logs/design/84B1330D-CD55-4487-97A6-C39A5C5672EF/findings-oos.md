### OOS_1: Ephemeral warning marker will be copied into committed design logs
- **Description**: Ephemeral warning marker will be copied into committed design logs. Scenario: `.missing-guideline-assessment-warning` is not in `_PUBLISH_EXCLUDE_*`, so degraded-path tmpdir markers can land in `larch-logs/design/<run-id>/` even though the committed execution issue already records the waiver.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/design/design_log_publish_flow.py:174-195
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] If the warning marker is kept, publish copy will commit it
- **Description**: [OUT_OF_SCOPE] If the warning marker is kept, publish copy will commit it. Scenario: _publish_excluded does not cover .missing-guideline-assessment-warning, so the degraded-path marker copied at lines 399-414 becomes a stray committed artifact beside execution-issues.md
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/design/design_log_publish_flow.py:174-194
- **Phase**: design



### OOS_3: Degraded warning marker will be copied into committed logs
- **Description**: Degraded warning marker will be copied into committed logs. Scenario: .missing-guideline-assessment-warning is a tmpdir sidecar like other excluded machine markers; without adding it to _PUBLISH_EXCLUDE_NAMES it lands in larch-logs/design runs
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/design/design_log_publish_flow.py:126-136
- **Phase**: design



