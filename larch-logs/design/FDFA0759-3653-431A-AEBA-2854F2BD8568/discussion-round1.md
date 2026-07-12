## Decision 1: Exact scope of "11 copies" and "9 nameWithOwner sites"
- **Question**: Which functions and inline sites are in-scope?
- **Resolution**: From codebase inspection:
  - 11 copy-functions: `clarify._resolve_repo_for_clarify`, `design_step0.resolve_repo`, `design_pause._resolve_repo`, `admission._resolve_repo`, `combine_issues._repo` (dead), `combine_issues._resolve_repo`, `issue_create._resolve_repo`, `issue_create._resolve_repo_for_fetch`, `issue_block._repo`, `analyze_bugs.resolve_repo`, `tracking_issue._resolve_repo_or_fail`
  - 9 inline `nameWithOwner` sites: `admission.py:61`, `issue_block.py:35`, `issue_create.py:370`, `analyze_issues.py:271`, `design_terminal.py:851`, `_report.py:811`, and the bodies of `clarify._resolve_repo_for_clarify`, `analyze_bugs.resolve_repo`, plus the dead `combine_issues._repo`
  - Out-of-scope: `forked_repo.py` (queries `nameWithOwner,parent,defaultBranchRef` together), `_plan_quality_commands._resolve_repo_script` (filesystem paths), `architectural_guidelines._resolve_repo_root` (filesystem paths), `calibration_replay._resolve_repo_path` (log file paths), `larch/git/gh.py` itself (canonical source)
- **Source**: codebase

## Decision 2: Files missing gh/proc imports
- **Question**: How to handle `admission.py`, `_report.py`, `analyze_issues.py` that use subprocess.run directly?
- **Resolution**: Add `from larch.core import proc` and `from larch.git import gh` to each. Replace inline subprocess calls with `gh.resolve_repo(proc)`. This matches the pattern already used in issue_create.py, issue_block.py, etc.
- **Source**: codebase

## Decision 3: Whether to delete or simplify existing wrapper functions
- **Question**: Should thin wrappers like `_resolve_repo_for_fetch` and `_resolve_repo_for_clarify` be deleted or just simplified?
- **Resolution**: Simplify bodies (replace inline logic with `gh.resolve_repo`), but keep function names where test files mock them by name (e.g., `analyze_issues._detect_repo`). Delete dead code (`combine_issues._repo`).
- **Source**: codebase (test_analyze_issues.py uses monkeypatch.setattr on `_detect_repo`)

## Decision 4: Hard constraints - what must not break
- **Question**: Which callers have specific error handling that must be preserved?
- **Resolution**: `_resolve_repo_for_clarify` raises `_ClarifyRepoResolutionError` on failure; preserve that by checking `gh.resolve_repo` return. `tracking_issue._resolve_repo_or_fail` raises `CliFailure`; preserve that. `analyze_bugs.resolve_repo` raises `AnalyzeBugsError`; preserve that. In all cases, simplify only the resolution step, not the error-handling layer above.
- **Source**: codebase
