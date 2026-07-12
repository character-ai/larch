### OOS_2: Testing step cites wrong pyright authority
- **Description**: Testing step cites wrong pyright authority. Scenario: Step 4 says "command prescribed by docs/linting.md", but that file only mentions pyright in CI prose; the concrete command is cd python && pyright in python/README.md and Makefile.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/tests/lint/test_lint_engine.py
- **Phase**: design

