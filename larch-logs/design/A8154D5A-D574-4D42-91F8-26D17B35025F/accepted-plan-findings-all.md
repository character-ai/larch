### FINDING_1: Pylint `skip-file` is missing from the grammar
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The accepted suppression grammars omit file-wide `# pylint: skip-file`, even though production modules already use it. That leaves existing file-level pylint silences invisible to the ratchet and lets new bare `skip-file` comments bypass G-Py-11.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `# pylint: skip-file # reason` (same-line reason only, matching the plan’s file-level rule), a `suppression_kind` for it, regex/token checks, bootstrap baseline rows, and pytest coverage; keep `disable=all` on the existing `disable=` path`
  - From Cursor-Innovation: Add file-level `# pylint: skip-file # reason` to accepted shapes, treat bare skip-file as a violation, baseline grandfathered rows, and add pass/fail tests mirroring the pylint disable cases


### FINDING_4: Baseline write-shrink coverage is missing
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The acceptance list checks stale rows, but it does not require a write-time shrink test for the baseline. That leaves `--write` unproven when live violations disappear, so the ratchet could keep obsolete baseline rows instead of shrinking them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `test_write_preserves_reasons_and_shrinks_obsolete_rows` (or equivalent) to the mandated pytest list, matching the tempfile-dir pattern


### FINDING_6: Production scan scope is too narrow
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: major
- **Concern**: The planned scanner only covers `python/larch/**/*.py`, but the feature spec requires enforcing G-Py-11 across production `python/` modules. That leaves top-level runtime files outside the ratchet, so new bare suppressions there would still pass locally and in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Broaden the scanner, pre-commit hook, and docs to `python/**/*.py` production modules, while keeping the existing test/helper/cache/vendor exclusions and the same baseline format.
  - From Cursor-Pragmatic: Reuse the python/**/*.py production iterator and exclusions from lint_subprocess_via_runner.py (skip test_*.py, conftest.py, test_support.py, review_test_support.py, tests/, etc.), or explicitly narrow the issue/acceptance text to python/larch/** and document the carve-out for root harness modules
  - From Codex-Pragmatic: Expand the iterator and baseline validation to all production `python/**/*.py` files, keeping the test/helper/vendored/cache exclusions, and widen the pre-commit file filter to match that scope.


### FINDING_8: `pylint: disable-next=` is not covered
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: The planned pylint grammar only covers `disable=...`, so existing and new `# pylint: disable-next=...` suppressions remain outside the ratchet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add `disable-next=` to the supported pylint grammar and add direct tests for it.


### FINDING_10:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:5-6
- **Concern**: [SCOPE-REDUCTION] The ratchet only scans `python/larch/**/*.py` and excludes helper and top-level Python modules, so it will not enforce G-Py-11 repo-wide.. Scenario: New unreasoned suppressions in files like `python/pytest_sharding.py:67` or `python/test_support.py:39-44` would still pass local lint, pre-commit, and CI, so the feature lands incomplete against the stated `python/` scope.
- **Proposed resolution**: Broaden the scan and baseline scope to the intended `python/**/*.py` surface, then keep only the explicit vendored/cache/venv exclusions and any truly intentional helper exemptions documented in the plan.


### FINDING_4: Bare valid suppressions must still be violations
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Valid suppression-family comments without the required code or reason can slip through if the scanner only recognizes the accepted code-bearing forms. Those bare suppressions should be reported as violations rather than treated as plain comments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Treat valid suppression-family comments that omit the required code or reason as violations, not plain comments. Add focused cases for bare noqa, ruff noqa, and type ignore.
  - From Codex-Requirements: Add explicit violation handling and focused tests for bare valid suppression forms so unsupported broad suppressions fail rather than being treated as plain comments.


### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:5-7,59-77
- **Concern**: [SCOPE-REDUCTION] Do not inherit the sibling lints' owner-module skips; keep the full production `python/**/*.py` scope in view.. Scenario: If the implementation copies `lint_subprocess_via_runner.iter_source_files` or `lint_env_via_config_constant.iter_source_files` verbatim, `python/larch/core/config.py:353` and any similar owner files stay outside the ratchet, so existing suppression debt and future bare suppressions there will still pass locally and in CI.
- **Proposed resolution**: Build a local iterator that only excludes tests, helper filenames, symlinks, cache, vendored, and virtualenv dirs. Do not carry over the `proc.py` or `config.py` self-exclusion from sibling lints.


