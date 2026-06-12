### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tracking_issue.py:read_main
- **Concern**: [SCOPE-REDUCTION] Read-mode summary skip list is underspecified versus shell. Scenario: Plan names marker families in prose but does not pin the exact first-line patterns from scripts/tracking-issue-read.sh (metadata/diagrams/plan/token-report/final-summary runid variants plus legacy implement-anchor). A partial port can leave summary comments in task.md and break the feedback-loop guard on issue and issue-plus-prompt reads
- **Proposed resolution**: Add an explicit constant list matching scripts/tracking-issue-read.sh:427-434 (both <!-- larch:diagrams v1 --> and <!-- larch:diagrams v1 runid=… --> forms) and test one representative row per pattern
