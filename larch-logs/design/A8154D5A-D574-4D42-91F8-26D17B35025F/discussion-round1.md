## Decision 1: Scanner scope
- **Question**: Should the lint scan all of `python/` or only `python/larch/` production modules?
- **Resolution**: Scan `python/larch/` production modules (matching every sibling lint: `lint_shared_convention_regex.py`, `lint_subprocess_via_runner.py`, etc.). Test files under `tests/` and files matching `test_*.py` are excluded. The issue's phrase "Scan `python/`" refers to the repo directory, not a mandate to include test infrastructure.
- **Source**: codebase

## Decision 2: File-level suppression placement rule
- **Question**: What placement rule should apply for file-level suppressions (e.g., module-header `# pylint: disable=...`, `# ruff: noqa: CODE`)?
- **Resolution**: Same-line reason only. A file-level suppression on a line by itself must carry `# reason text` inline on the same line (extending the suppression directive), matching the inline grammar: `# ruff: noqa: CODE - reason` or `# pylint: disable=check  # reason`. Adjacent preceding-line reasons are NOT accepted in v1 (simple, consistent, and keeps the lint's line-level model uniform).
- **Source**: codebase + designer call (issue delegated this decision to the designer)

## Decision 3: Pragma for intentional exemptions
- **Question**: Should the lint support an inline pragma to suppress specific lines without a baseline entry?
- **Resolution**: No pragma in v1. The baseline covers all existing violations. The lint module itself must carry reasons (self-applying). If future edge cases arise, a pragma can be added in a follow-up. This keeps the initial implementation minimal.
- **Source**: codebase + designer call
