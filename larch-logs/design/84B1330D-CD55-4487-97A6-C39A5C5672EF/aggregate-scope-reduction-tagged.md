### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/design/design_log_publish_flow.py
- **Concern**: [SCOPE-REDUCTION] Degraded path adds a second tmpdir marker on top of the execution issue. Scenario: The plan writes both a Warnings execution issue and .missing-guideline-assessment-warning, then design_summary.py reads the marker. That duplicates state and the marker is not in _publish_excluded, so it can land in committed design logs as noise
- **Proposed resolution**: Drive the summary prefix from the committed Warnings entry (or a single KV written into execution-issues.md) and drop .missing-guideline-assessment-warning unless publish filter excludes it
