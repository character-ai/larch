### OOS_2: [OUT_OF_SCOPE] Failed Cursor auto-fix timing rows are skipped
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: A pre-existing caller passes `--status failed`, which the timing ledger rejects, so failed Cursor auto-fix rows are not recorded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


