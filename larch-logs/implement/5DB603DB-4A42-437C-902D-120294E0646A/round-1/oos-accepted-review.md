### OOS_1: [OUT_OF_SCOPE] Test name claims unrelated-git coverage but mocks held check
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `test_try_remove_stale_index_lock_ignores_unrelated_git_process` mocks `_index_lock_is_held` instead of exercising `_repo_scoped_git_process_detected`. Repo-scoped detection regressions (such as substring false positives) would not be caught. Add a test that exercises repo-scoped process detection without patching the held check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Branch bundles unrelated #4878 index.lock work with progress-report fix
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-quiet-stdout-output.txt
- **Severity**: important
- **Concern**: The branch bundles the progress-report fix with unrelated `python/git.py` index.lock retry logic and `python/review_and_fix.py` commit-path changes (issue #4878). Review and acceptance scope exceed the progress-report plan. A regression in lock removal or review-and-fix commit staging can stall `/implement` review rounds while reviewers believe they are merging only the progress hook fix. Split #4878 to its own PR, or explicitly dual-scope the PR, update plan/acceptance, and run full `py-test` plus review-and-fix harnesses before merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Split #4878 to its own PR or explicitly dual-scope the PR and run full py-test + review-and-fix harnesses before merge.
  - From dyn-quiet-stdout-output.txt: Address the concern above.


