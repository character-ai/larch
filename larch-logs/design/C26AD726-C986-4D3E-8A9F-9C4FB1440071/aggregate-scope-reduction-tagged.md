### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-implement-anti-polling-rule.md:1-67
- **Concern**: [SCOPE-REDUCTION] Deleted anti-polling harness leaves its companion doc with extinct notification-stack tokens. Scenario: The plan deletes scripts/test-implement-anti-polling-rule.sh and adds an extinct-token harness that excludes only larch-logs, but the companion markdown still contains design-background-wait, silent yield, and premature notification, so the new acceptance grep fails
- **Proposed resolution**: Delete scripts/test-implement-anti-polling-rule.md with the harness or explicitly rewrite it so none of the extinct tokens remain
