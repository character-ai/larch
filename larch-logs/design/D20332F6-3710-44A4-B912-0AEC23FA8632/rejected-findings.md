### [Plan Review] FINDING_4

### FINDING_4: design_publish._write_result_env empty-row wire semantics unspecified
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `design_publish._write_result_env` repoint omits empty-row wire semantics that `design_postplan` documents. Current `"\n".join(...) + "\n"` writes a lone `\n` when `rows` is empty; `design_postplan` explicitly preserves empty-dict → empty file. Repointing both through `format_kvs`/`write_kvs` without noting publish’s list input can change on-disk bytes for empty env files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `### UPDATED: python/design_publish.py`, state whether empty `rows` must stay a lone `\n` (wrapper writes `"\n"` explicitly) or become a zero-byte file like postplan; add a focused parity test if empty publish env is reachable


