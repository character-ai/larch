### OOS_1: [SCOPE-REDUCTION] Marker stores search state and selected_count beyond the issue minimum
- **Description**: [SCOPE-REDUCTION] Marker stores search state and selected_count beyond the issue minimum. Scenario: Issue #1 only requires run_date and highest_closed_issue_number_scanned; extra audit-context fields are not read by the nudge and expand the committed contract without clearing completeness or correctness gates
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/learn_from_bugs.py
- **Phase**: design



