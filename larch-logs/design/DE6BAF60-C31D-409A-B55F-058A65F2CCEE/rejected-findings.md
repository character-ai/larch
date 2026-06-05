### [Plan Review] FINDING_2

### FINDING_2: Happy-path temp-home cleanup check can avoid global /tmp diffing
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Concern**: The planned global `/tmp` `larch-codex-home-*` snapshot helper is unnecessary for the happy path because the stub already records the temp home via `STUB_CODEX_HOME_FILE`; global `/tmp` diffing adds concurrency noise tolerance only needed when the stub never runs in the 4h auth-prep-failure case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: For happy-path only assert [[ ! -d "$(cat "$CODEX_HOME_FILE")" ]] after launch; keep the /tmp before/after snapshot solely for the 4h case


