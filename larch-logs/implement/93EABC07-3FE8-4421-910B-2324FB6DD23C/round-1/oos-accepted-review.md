### OOS_1: [OUT_OF_SCOPE] Design publish residual-check asymmetry predates branch
- **Reviewer(s)**: dyn-secret-counts-output.txt
- **Severity**: latent
- **Concern**: `_copy_tree_redacted` writes `scrub_log_secrets()` output but does not perform the fail-closed residual check that `_scrub_run_tree` (`python/run_logs.py:1646-1649`) applies on the implement commit path. That asymmetry predates this branch's count plumbing; the new unit test confirms byte/count parity on the happy path but does not add fail-closed coverage.
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_2: [OUT_OF_SCOPE] `_larch_log_commit` warning helper on dead production path
- **Reviewer(s)**: dyn-secret-counts-output.txt
- **Severity**: latent
- **Concern**: `_larch_log_commit` still owns `_warn_secret_scrub` and is no longer called from production code (only tests). This dead-path split predates the branch; the branch correctly moved active callers to `_commit_run` but did not relocate the loud warning helper to the live path.
- **Suggested revisions (informational for voters; coder decides)**:
