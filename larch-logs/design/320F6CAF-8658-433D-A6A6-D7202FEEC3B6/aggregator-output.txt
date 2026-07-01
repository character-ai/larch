### FINDING_1: Repo-wide `lint:` does not run `lint-flat-tests`
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: `lint-flat-tests` is only wired into `py-lint-checks-fast`, not the repo-wide `lint:` aggregate. A developer can add a new root `python/test_*.py` and still pass `make lint`, because the canonical lint entrypoint never runs the new ratchet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add `lint-flat-tests` to the `lint:` prerequisite list so the standard repo-wide lint command enforces the same flat-test ratchet as CI.

### FINDING_2: Move subsections omit mandatory delete of flat source modules
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Move subsections omit mandatory delete of flat source modules. Only the tier1a move lists "Delete the old root file as part of the move." The bg-wait and skill-description-length subsections say "Create by moving" but never require removing `python/test_lint_bg_wait_coverage.py` or `python/test_lint_skill_description_length.py`. A copy-only implement leaves three extra flat `test_*.py` files, so `lint flat-tests` and acceptance ("no flat test_*.py at python/ root except exempt helper") fail until someone notices.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add the same explicit delete bullet to both remaining move subsections, or one Approach-level rule: every relocated `python/test_lint_*.py` source is removed (prefer `git mv`) so only `python/test_support.py` stays flat.

### FINDING_3: Relocated lint tests drop out of `checks run-relevant` coverage
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: Moving `python/test_lint_tier1a.py` and `python/test_lint_skill_description_length.py` under `python/tests/lint/` without updating `checks_run_relevant.py` drops them from the broad `python/*.py` run-relevant fallback. Only the bg-wait tuple is updated in the plan sketch, so edits to the relocated tier1a and skill-description-length tests no longer enqueue `test-lint-tier1a-size`, `test-lint-skill-description-length`, or the broader `py-test` validation that still exercises those moved tests during `/implement`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add explicit direct-target rows for the two moved paths, or broaden the relevant-check pattern to cover python/tests/lint/test_lint_*.py.
  - From Codex-Pragmatic: Add explicit direct-target rows for the two relocated tests, or preserve a nested-path fallback that still triggers `py-test` for `python/tests/lint/test_lint_*.py` changes.
