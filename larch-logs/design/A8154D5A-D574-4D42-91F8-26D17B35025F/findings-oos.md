### OOS_1: Plan scope bullets exclude `tests/` but the referenced iterator does not
- **Description**: Plan scope bullets exclude `tests/` but the referenced iterator does not. Scenario: The bullets require excluding `tests/`, while the implementation note copies `lint_subprocess_via_runner.iter_source_files`, whose `EXCLUDED_DIRS` omit `tests/`. Today every file under `python/tests/` is already skipped by the `test_*.py` filename rule, so behavior matches intent, but the mixed guidance invites an unnecessary `tests/` exclusion fork.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_subpression_reason.py
- **Phase**: design



