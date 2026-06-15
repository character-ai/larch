## Decision 1: Test file exclusion mechanism
- **Question**: How should test files be excluded from the installed plugin given that cone-mode sparse checkout cannot filter within directories?
- **Resolution**: Post-install cleanup added to `upgrade_larch.py` (after `claude plugin install`). Deletes test files from the installed cache directory by pattern.
- **Source**: user

## Decision 2: Directories to remove from sparse cone
- **Question**: Which top-level directories should be removed from `LARCH_SPARSE_DIRS`?
- **Resolution**: Remove `.github/` (CI workflows), `.claude/` (dev rules/settings/skills), `.gemini/` (Gemini dev skills), and `tests` (directory does not exist). New list: `.claude-plugin agents docs hooks python scripts skills`.
- **Source**: user

## Decision 3: Test file cleanup patterns
- **Question**: What exact file patterns should the cleanup remove?
- **Resolution**: Python: `python/test_*.py`, `python/conftest.py`, `python/pyproject.toml`, `python/ruff.toml`. Bash: `scripts/test-*.sh`, `scripts/test-*.md`, `skills/*/scripts/test-*.sh`, `skills/*/scripts/test-*.md`. Root: `parallel-tests.py`, `Makefile`.
- **Source**: user + codebase

## Decision 4: Initial install coverage
- **Question**: Should cleanup also cover first-time installs (not via /upgrade-larch)?
- **Resolution**: Upgrade script only. Initial installs keep test files until the user first runs /upgrade-larch. No SessionStart hook change.
- **Source**: user

## Decision 5: pytest/ruff config files
- **Question**: Should `python/conftest.py`, `python/pyproject.toml`, and `python/ruff.toml` also be cleaned up?
- **Resolution**: Yes, remove all three. None are used at plugin runtime; all are dev/test infrastructure.
- **Source**: user
