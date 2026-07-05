### [Plan Review] FINDING_5

### FINDING_5: Serialization fixtures still assume OOS blocks without Vote tally are eligible
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan omits updates to serialization fixtures that still assume OOS blocks without an accepted Vote tally line remain eligible. If `_is_vote_tally_eligible` is tightened to require `Vote tally: Result=accepted`, these fixtures will fail or silently preserve the old contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Expand the test_oos.py update step to explicitly revise test_oos_serialize_prose_result_not_rejected, test_oos_serialize_result_token_boundaries, and any similar fixtures, plus add the planned no-tally regression.


