### FINDING_11: Cleanup may delete active sessions (top-level mtime only)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Cleanup prunes session trees by top-level mtime only, not newest in-tree activity (`skills/cleanup/scripts/cleanup.sh:39-43,81-85`). An active `/implement` or `/design` session can keep writing under a cache entry whose top-level directory is older than `LARCH_CLEANUP_RETENTION_DAYS`; `/cleanup` may delete the whole tree including secrets and `CMD_JSON` sidecars while Claude still runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Restore descendant activity scanning or touch session roots on writes; avoid deleting when any descendant is newer than the cutoff; fail closed on `find` errors.


### FINDING_5: Missing test-ship-pr.md for append_tool_failure_local fallback coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: New `append_tool_failure_local` fallback relay coverage (`scripts/test-ship-pr.sh:6094-6122`) lacks the sibling `scripts/test-ship-pr.md` update required by plan acceptance. Future harness edits won't be discoverable; script-md-sibling convention drifts; reviewers miss merged `2>&1` and BEL/ESC contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a test-ship-pr.md bullet documenting fallback forcing, fixture, and assertions (mirror other relay harness .md files).


