## Proposed Design Outline

### Goals
- Add `issue_list_read` wrapper routing through `_retry_read` + `loads_json_paginated_list`.
- Add `issue_close` wrapper for all close-argv shapes used across `python/larch/`.
- Fill any view/edit coverage gaps found by auditing 8 view + 11 edit/close raw-argv shapes.

### Non-goals
- Caller repointing (handled in sibling issues blocked by this one).
- Behavior changes to existing wrappers.
- New CLI verbs or module-level commands.

### Approach sketch
- Audit raw-argv shapes in `python/larch/` against existing `issue_view_*` / `issue_edit*` wrappers; record coverage gaps.
- Add `issue_list_read(runner, *, repo, state, labels, search, fields, paginate)` via `_retry_read`; parse result with `loads_json_paginated_list`.
- Add `issue_close(runner, issue, *, repo=None, reason=None, comment=None)` via `_gh`; return `CommandResult`.
- Add any additional gap wrappers (e.g., plain `issue_view_read` for no-JSON view callers) if the audit finds uncovered shapes.
- Add tests in `python/tests/git/test_gh.py` for every new function.

### Surfaces in scope
- `python/larch/git/gh.py`
- `python/tests/git/test_gh.py`

### Open questions
- None.
