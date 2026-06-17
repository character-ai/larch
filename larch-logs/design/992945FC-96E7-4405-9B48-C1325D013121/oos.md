### OOS_1:
- **Description**: Fake tally stub still emits a 3-column reviewer_slots header. Scenario: Pipeline tests that stub classification emission may not match the new 22-column three-slot shape after test_review_tally.py moves to FINDINGS_CLASSIFICATION_HEADER
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/review_test_support.py:286-287
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

