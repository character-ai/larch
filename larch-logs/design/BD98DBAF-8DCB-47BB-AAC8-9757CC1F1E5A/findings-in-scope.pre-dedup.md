### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/test_plan_review.py:29-37
- **Concern**: [SCOPE-REDUCTION] Item 2 adds three regional function-body slices for COLLECT_FAILURE_COUNT pinning. Scenario: Item #4602 only needs a count-path regression pin; regional slicing helpers plus 40-line co-occurrence fallback add brittle machinery that can fail on harmless refactors while body-wide pins in test_embedded_plan_review_loop_uses_migrated_collector already cover the contract
- **Proposed resolution**: Limit Item 2 to one new test with exact COLLECT_FAILURE_COUNT=0 plus one emit-path substring (round-summary.env + COLLECT_FAILURE_COUNT) in the embedded plan-review-loop body; drop helper-region extraction unless a slice fails on first pass

