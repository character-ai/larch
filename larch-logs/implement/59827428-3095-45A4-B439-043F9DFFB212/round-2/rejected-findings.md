### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Non-rollup annotate coverage is missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: After the `_annotate_accepted_urls` refactor, `test_design_oos.py` still lacks a success-path regression for a non-rollup batch with two combined blocks, so distinct per-slot `Filed URL` and `OOS_FILE_MAP` rows can regress silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

