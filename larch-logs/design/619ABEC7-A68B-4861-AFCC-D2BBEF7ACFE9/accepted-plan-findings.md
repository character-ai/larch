### FINDING_1: Composite checks do not propagate persisted `REPO_ROOT`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Composite checks invoked through `implement checks-commit-route` and `checks-step5-resume` do not pass the validated session `REPO_ROOT` to `checks run-relevant`. Because `default_repo_root` prefers `CLAUDE_PROJECT_DIR` over the persisted root, checks can execute against a different tree than the one used to compute and persist the run identity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/larch/implement/dispatch_commit_route.py: resolve validated REPO_ROOT from session-env.sh (mirror step-8-assessment.sh), pass --repo-root to every checks run-relevant argv in _run_relevant_checks_for_site, and run the leg with cwd set to that root. Extend python/tests/implement/test_implement_dispatch.py to pin the passthrough and add a regression where CLAUDE_PROJECT_DIR points elsewhere but checks still execute against persisted REPO_ROOT.
  - From Cursor-Innovation: Mirror step-8-assessment.sh: pass --repo-root "$REPO_ROOT" in build_child_command and in checks-commit-route legs; add a subprocess regression where CLAUDE_PROJECT_DIR differs from persisted REPO_ROOT
  - From Cursor-Pragmatic: Add `### UPDATED: python/larch/implement/dispatch_commit_route.py` (and pin `--repo-root` from session `REPO_ROOT` in `_run_relevant_checks_for_site`, or teach `default_repo_root()` to prefer persisted `REPO_ROOT`) plus a regression that `CLAUDE_PROJECT_DIR` differs from session `REPO_ROOT`.


### FINDING_2: Child mode publishes launch identity without revalidation
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: major
- **Concern**: The child can run checks against a repository that changed after the parent computed the launch identity, then publish the parent-computed identity as though it described the checked inputs. This permits the foreground caller or later rejoin logic to consume or reuse a result whose recorded identity does not match the inputs actually checked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: After entering the validated repository root and before invoking the checks CLI, recompute the identity and fail without publishing a terminal result if it differs from the seeded identity. Preserve the verified identity only after this check passes.
  - From Codex-Requirements: Recompute identity in child mode before checks and before terminal publication. Require both values to match the immutable launch identity. On mismatch, publish a non-reusable integrity failure. Add a subprocess regression that mutates the repository between identity seeding and child execution.


