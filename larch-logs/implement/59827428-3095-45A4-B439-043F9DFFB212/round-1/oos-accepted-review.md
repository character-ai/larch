### OOS_1: [OUT_OF_SCOPE] cap-1 dedup stdout slot lacks regression coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The dedup-only cap-1 stdout shape is untested, so a regression in successful slot parsing could prevent all originals from mapping to the same URL.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a cap-1 test using ISSUE_1_DUPLICATE_OF_URL and assert both originals and OOS_FILE_MAP rows match the URL case


