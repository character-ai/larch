### OOS_1: [OUT_OF_SCOPE] `_lint_fix_delta_paths` tests do not cover untracked inclusion branch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: New `_lint_fix_delta_paths` tests stub untracked capture to `[]`, so the untracked inclusion branch in `review_and_fix.py:1156-1157` is unverified. If lint-fix reports a newly created untracked file that does not appear in `git diff --name-only` against `pre_lint_head`, a regression could drop it from the lint commit without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a unit test with unioned_delta_paths=("new.py",), empty current_diff_paths, and _capture_round_untracked_paths returning ["new.py"].


