### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/tests/review/test_review_tally.py:230-2950; python/tests/review/test_plan_review.py:1846-4261
- **Concern**: [SCOPE-REDUCTION] The plan modifies acceptance suites that must pass unchanged. Scenario: These suites already cover the listed tally paths. Editing them violates the explicit acceptance contract and needlessly enlarges the diff
- **Proposed resolution**: Remove their UPDATED headings. Run them unchanged and keep new coverage in the focused engine and parser tests
