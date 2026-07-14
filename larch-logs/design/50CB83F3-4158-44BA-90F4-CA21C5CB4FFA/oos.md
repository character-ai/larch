### OOS_1: Discovery omits the standard python/ EXCLUDED_DIRS skip set used by sibling AST linters
- **Description**: Discovery omits the standard python/ EXCLUDED_DIRS skip set used by sibling AST linters. Scenario: Other python-wide linters skip .venv, __pycache__, node_modules, and .agents during rglob; this plan only exempts python/larch/git/. A local python/.venv or cache tree could add false positives or noise, though CI clones typically omit those paths.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/lint/lint_gh_argv_literal.py
- **Phase**: design

Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

