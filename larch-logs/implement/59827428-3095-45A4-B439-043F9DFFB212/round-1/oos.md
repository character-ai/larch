### FINDING_4: [OUT_OF_SCOPE] cap-1 dedup stdout slot lacks regression coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The dedup-only cap-1 stdout shape is untested, so a regression in successful slot parsing could prevent all originals from mapping to the same URL.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a cap-1 test using ISSUE_1_DUPLICATE_OF_URL and assert both originals and OOS_FILE_MAP rows match the URL case


Vote tally: YES=2 NO=0 JUDGE_ERROR=1 Result=accepted

### FINDING_5: [OUT_OF_SCOPE] TSV precedence fallback test missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Legacy `FINDING_N` blocks have no dedicated TSV-precedence regression, so a conflicting TSV/footer pair could still be misread if that path changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add FINDING_N fixture with conflicting TSV/footer when extending audit coverage later


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected

