### FINDING_1: Incremental coverage advancement contract is incomplete
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The planned incremental advancement path does not fully specify how safe post-assessment HEAD drift is detected, how covered identity is recomputed, or how snapshot artifacts stay aligned. Without an explicit stored-HEAD..current-HEAD incremental check, implementers may diff from base or replay the full materialized diff and misclassify pre-assessment paths as new increments. Without full-diff fingerprint recomputation and atomic snapshot refresh during advancement, safe docs-only or larch-logs-only advances can leave `COVERED_DIFF_FINGERPRINT`, `DIFF_SNAPSHOT`, and live consumption checks inconsistent, forcing reassessment despite the once-per-run pre-filter intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: State explicitly that the rename-safe incremental check runs git diff --no-renames --name-only -z <stored HEAD_SHA>..<current HEAD>, using the durable metadata HEAD_SHA written at the last successful coverage update as the old revision.
  - From Cursor-Pragmatic: In the shared advancement helper, re-materialize the full base..HEAD implementation diff at the new HEAD, atomically update the snapshot file plus `DIFF_SNAPSHOT`, `COVERED_DIFF_FINGERPRINT`, and `HEAD_SHA` together, and add tests that a docs-only or log-only advance leaves snapshot bytes and covered identity consistent.
  - From Cursor-Pragmatic: After incremental paths pass classification, materialize the full implementation diff at the new HEAD, set `COVERED_DIFF_FINGERPRINT` to that full-diff fingerprint (keeping `AUTHORED_DIFF_FINGERPRINT` unchanged), and test chained docs-only then log-only advances against live full-diff consumption.


