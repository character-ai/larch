### FINDING_3: Missing branch for exit 0 with PUBLISH_OK=false and no RECOVERY_BRANCH
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The new `design publish` branching covers scrub-fatal (`returncode != 0` without `RECOVERY_BRANCH`) and recoverable push/PR misses (`returncode == 0` with `RECOVERY_BRANCH`), but not the third live path: `returncode == 0`, `PUBLISH_OK=false`, and no `RECOVERY_BRANCH`. Worktree/init failures and other non-scrub publish misses in `design_log_publish_flow.py` already exit 0 with `PUBLISH_OK=false` and no recovery branch; an implementer following only steps 1-4 could mis-route these cases or drop `PUBLISH_OK=false` from the result env while still returning 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add an explicit recoverable branch: when `publish.returncode == 0`, parsed `PUBLISH_OK=false`, and `RECOVERY_BRANCH` is absent, preserve today's exit 0 behavior (no rotation warning unless publish actually succeeded with `SECRET_SCRUB_VIOLATIONS > 0`) and regression-test a worktree/init failure fixture


