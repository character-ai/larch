### OOS_1: [OUT_OF_SCOPE] Lint-fix commit path lacks cwd regression test coverage
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: New tests verify cwd only for two commit helpers via mocked `_run`; the lint-fix commit path and subdirectory CWD integration are untested. A regression in `_commit_lint_fix_delta_paths` or rev-parse-only repo resolution could ship without test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add `test_commit_lint_fix_delta_paths_passes_repo_root_as_cwd` and/or an `os.chdir` subdirectory integration case.


