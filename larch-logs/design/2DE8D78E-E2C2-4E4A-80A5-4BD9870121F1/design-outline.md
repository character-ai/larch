## Proposed Design Outline

### Goals
- Eliminate 8+ divergent issue-list reimplementations by routing every caller through `gh.issue_list_read`.
- Delete `issue_create._json_documents`; replace its call site with `gh.loads_json_paginated_list`.
- Clear the `SLF001 noqa` at `audit_runs.py:141` once the public wrapper exists.

### Non-goals
- No changes to command output formats or external-facing behavior.
- No new parameters or pagination modes added to `gh.issue_list_read`.
- No refactoring of code unrelated to issue listing within the scope files.

### Approach sketch
- Add `from larch.git import gh` import to `learn_from_bugs.py` (only file missing it).
- Replace each inline `proc.run(["gh", "issue", "list", ...])` / `gh._gh(...)` block with `gh.issue_list_read(proc, ...)`.
- Replace each inline `gh api --paginate repos/{repo}/issues` block with `gh.issue_list_read(proc, ..., limit=100000)`.
- In `analyze_issues.py:fetch_main`: use two `gh.issue_list_read` calls (expanded then fallback fields) instead of `subprocess.run`; write result via existing `_write_issue_dump`.
- Update all unit tests to mock `gh.issue_list_read` instead of raw `proc.run` / `subprocess.run`.

### Surfaces in scope
- `python/larch/issue/analyze_bugs.py`
- `python/larch/issue/learn_from_bugs.py`
- `python/larch/issue/analyze_issues.py`
- `python/larch/issue/audit_runs.py`
- `python/larch/issue/combine_issues.py`
- `python/larch/issue/deps_audit.py`
- `python/larch/issue/issue_create.py`
- `python/larch/issue/rejected_analysis.py`
- `python/tests/issue/test_*.py` for all above
- `skills/voter-calibration/scripts/voter-calibration.py` (transitive; no direct changes expected)

### Open questions
- None.
