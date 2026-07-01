### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:80-88
- **Concern**: `lint-flat-tests` is only wired into `py-lint-checks-fast`, not the repo-wide `lint:` aggregate.. Scenario: A developer can add a new root `python/test_*.py` and still pass `make lint`, because the canonical lint entrypoint never runs the new ratchet.
- **Proposed resolution**: Add `lint-flat-tests` to the `lint:` prerequisite list so the standard repo-wide lint command enforces the same flat-test ratchet as CI.



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_lint_bg_wait_coverage.py:1; python/test_lint_skill_description_length.py:1
- **Concern**: Move subsections omit mandatory delete of flat source modules. Scenario: Only the tier1a move lists "Delete the old root file as part of the move." The bg-wait and skill-description-length subsections say "Create by moving" but never require removing `python/test_lint_bg_wait_coverage.py` or `python/test_lint_skill_description_length.py`. A copy-only implement leaves three extra flat `test_*.py` files, so `lint flat-tests` and acceptance ("no flat test_*.py at python/ root except exempt helper") fail until someone notices.
- **Proposed resolution**: Add the same explicit delete bullet to both remaining move subsections, or one Approach-level rule: every relocated `python/test_lint_*.py` source is removed (prefer `git mv`) so only `python/test_support.py` stays flat.



### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/checks_run_relevant.py:423-457
- **Concern**: Moved lint tests lose run-relevant coverage. Scenario: The plan moves python/test_lint_tier1a.py and python/test_lint_skill_description_length.py under python/tests/lint/, but only the bg-wait tuple is updated. The broad python/*.py rule no longer matches those files, so /implement checks run-relevant stops scheduling test-lint-tier1a-size and test-lint-skill-description-length on edits to the relocated tests.
- **Proposed resolution**: Add explicit direct-target rows for the two moved paths, or broaden the relevant-check pattern to cover python/tests/lint/test_lint_*.py.



### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/checks_run_relevant.py:496
- **Concern**: Moving `python/test_lint_tier1a.py` and `python/test_lint_skill_description_length.py` under `python/tests/lint/` drops them out of the only broad `python/*.py` run-relevant fallback.. Scenario: `checks run-relevant` on edits to either relocated test will stop enqueueing `py-test`, so `/implement` can skip the validation that still exercises those moved tests.
- **Proposed resolution**: Add explicit direct-target rows for the two relocated tests, or preserve a nested-path fallback that still triggers `py-test` for `python/tests/lint/test_lint_*.py` changes.



