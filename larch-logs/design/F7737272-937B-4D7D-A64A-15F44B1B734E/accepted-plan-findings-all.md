### FINDING_1: Update the live design closure regression test
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Closure Ratchet Auditor
- **Severity**: major
- **Concern**: The real design-scan regression test still expects the two demoted shared files to be eager closure members, so verification will fail after the SKILL.md demotion even if the closure scan and baseline are otherwise correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/tests/lint/test_lint_skill_closure_growth.py: remove or invert the four assertions for those paths (absent from both eager and conditional tiers) and run python3 -m pytest python/tests/lint/test_lint_skill_closure_growth.py in Testing strategy
  - From Codex-Arch: Update `test_real_design_scan_keeps_plan_review_eager_and_branch_refs_conditional()` to expect both files removed from eager closure, and keep the baseline in sync.
  - From Cursor-Pragmatic: Add ### UPDATED: python/tests/lint/test_lint_skill_closure_growth.py: remove or invert those assertions (and assert both paths stay out of conditional_files if fully untracked). Add python -m pytest python/tests/lint/test_lint_skill_closure_growth.py to Testing strategy.
  - From Codex-Pragmatic: Update this test to drop those eager-file assertions and keep the remaining plan-review and conditional-file checks.
  - From Cursor-Requirements: Add ### UPDATED: python/tests/lint/test_lint_skill_closure_growth.py to firm files (or a testing-strategy step) that drops those two paths from result.files assertions and keeps plan-review.md eager plus branch refs conditional
  - From Codex-Requirements: Add or update the test expectation so the real design scan no longer requires those two files in `result.files` or `conditional_files`, and include that file in the plan if needed
  - From Cursor-dyn-Closure Ratchet Auditor: Add ### UPDATED: python/tests/lint/test_lint_skill_closure_growth.py to the plan: flip those assertions to assert both paths are absent from result.files and result.conditional_files; keep plan-review.md and conditional-file checks unchanged.


