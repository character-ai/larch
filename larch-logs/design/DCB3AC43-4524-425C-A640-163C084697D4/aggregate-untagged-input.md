### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review_tally.py:620-627
- **Concern**: Plan-review sole-finder detection can diverge from credit-sharing attribution when `split_classification_attribution` returns one token but comma fallback would yield multiple proposers. Scenario: Some co-proposed `finding_reviewers` cells can tokenize to a single label (or empty-then-single fallback segment) while comma-split would expose multiple proposers; those rows would still get sole-finder bonus under `len(split_reviewers)==1`
- **Proposed resolution**: Pin plan-review sole-finder detection to the same comma-split proposer list used for `score_rows.extend` (or require `len(comma_split) == 1` in addition to `len(split_reviewers) == 1`) so bonus gates cannot diverge from shared-credit attribution
