### OOS_3: Issue item 2 says scan `python/`; plan scopes to `python/larch/**/*.py` only
- **Description**: Issue item 2 says scan `python/`; plan scopes to `python/larch/**/*.py` only. Scenario: Top-level `python/*.py` harness modules currently have no suppressions, so behavior matches intent but diverges from issue wording
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: docs/linting.md (planned)
- **Phase**: design

### OOS_5: Reason validation accepts any non-empty trailing token
- **Description**: Reason validation accepts any non-empty trailing token. Scenario: Parallel to lint-agent-tool-contract, a reason of `--` or `.` could satisfy G-Py-11 cosmetically without reviewer-useful text
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/lint/lint_suppression_reason.py
- **Phase**: design

