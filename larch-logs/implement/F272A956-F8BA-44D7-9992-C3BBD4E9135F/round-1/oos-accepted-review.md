### OOS_1: [OUT_OF_SCOPE] Missing tests for comment-post-failed and label-remove-failed publish paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Unit tests omit `comment-post-failed` and `label-remove-failed` publish branches required by plan acceptance and Step 0b routing. A regression in post-plan-write comment or label steps (wrong `CLARIFY_PUBLISH_STATUS`, missing `PLAN_WRITE_OK=true`, or exit code != 1) could mis-route `/design` Step 0b clarify publish Final summary without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add tests that mock `clarify_comment_post` / `clarify_label` failures and assert result-env KVs.
  - From cursor-specialist-edge-cases-output.txt: Add focused tests mirroring `python/clarify.py` publish exception handlers.
  - From cursor-specialist-testing-output.txt: Add unit tests monkeypatching `clarify_comment_post` and `clarify_label` to fail after successful plan write; assert result env rows, `SUMMARY_OUTCOME`, and exit 1.


