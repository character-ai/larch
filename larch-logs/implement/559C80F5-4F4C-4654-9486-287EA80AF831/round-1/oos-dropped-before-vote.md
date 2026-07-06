### FINDING_8: [OUT_OF_SCOPE] Stale comment about the removed stall should be updated
- **Reviewer(s)**: dyn-dyn-bg-wait
- **Severity**: nit
- **Concern**: A comment still references the old task-output read stall even though Fix A removed it, so the maintainer context is misleading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bg-wait: Rewrite comment to reflect current Read allow and Bash-probe deny split.

### FINDING_9: [OUT_OF_SCOPE] Premature completed notifications remain an upstream issue
- **Reviewer(s)**: dyn-dyn-bg-wait
- **Severity**: nit
- **Concern**: The platform may still emit premature completed notifications on stdout inactivity, which is an upstream trigger we are only working around locally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bg-wait: File upstream report (Fix D); optional keepalive remains out of scope per plan.

### FINDING_16: [OUT_OF_SCOPE] Foreign-clone allow coverage is pre-existing
- **Reviewer(s)**: dyn-dyn-bg-wait
- **Severity**: nit
- **Concern**: `scripts/test-hook-bg-poll-guard.sh` still allows `cat tasks/foo.output` when only a foreign-clone marker is live, but that behavior predates this branch and is separate from the new `Read` carve-out.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bg-wait: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Repo-file reads outside the live tmpdir are unrelated
- **Reviewer(s)**: dyn-dyn-bg-wait
- **Severity**: nit
- **Concern**: Reads of repo files outside the live tmpdir were already hook-allowed before this change and remain unrelated to the `tasks/*.output` fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bg-wait: Address the concern above.

