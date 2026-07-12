## Proposed Design Outline

### Goals
- Replace every inline `["gh", "repo", "view", "--json", "nameWithOwner"]` construction with `gh.resolve_repo`.
- Delete or simplify the 11 local repo-resolution functions that duplicate `gh.resolve_repo` logic.
- Update tests that assert on the old argv or mock the removed functions.

### Non-goals
- Adding new resolution behavior or fallbacks beyond what `gh.resolve_repo` already provides.
- Changing `gh.resolve_repo` itself.
- Touching `forked_repo.py` (fetches `nameWithOwner,parent,defaultBranchRef` together; different query).
- Touching `*_resolve_repo_root` / `*_resolve_repo_path` functions (filesystem paths, not GitHub slugs).

### Approach sketch
- Enumerate all ~20 sites (11 copy-functions + 9 inline constructions) via the audit in discussion-round1.md.
- For each inline site: replace the `subprocess.run` / `proc.run` call with `gh.resolve_repo(proc)`.
- For each copy-function: simplify the body to call `gh.resolve_repo` (keep the function if tests mock it by name; delete if dead code or a trivially removable thin wrapper).
- Add `from larch.core import proc` and `from larch.git import gh` where missing (`admission.py`, `_report.py`, `analyze_issues.py`).
- Update tests that check argv `["gh", "repo", "view", "--json", "nameWithOwner", ...]` directly.

### Surfaces in scope
- `python/larch/issue/combine_issues.py` (dead `_repo`, `_resolve_repo`)
- `python/larch/issue/issue_block.py` (`_repo`)
- `python/larch/issue/issue_create.py` (`_resolve_repo`, `_resolve_repo_for_fetch`)
- `python/larch/issue/analyze_bugs.py` (`resolve_repo`)
- `python/larch/issue/analyze_issues.py` (`_detect_repo`)
- `python/larch/issue/tracking_issue.py` (`_resolve_repo_or_fail`)
- `python/larch/design/clarify.py` (`_resolve_repo_for_clarify`)
- `python/larch/design/design_step0.py` (`resolve_repo`)
- `python/larch/design/design_pause.py` (`_resolve_repo`)
- `python/larch/design/design_terminal.py` (inline in `file_issue_after_dedup`)
- `python/larch/state/admission.py` (`_resolve_repo`)
- `python/larch/state/_report.py` (inline in stall-recovery helper)
- Tests: `python/tests/design/test_clarify.py`, `python/tests/issue/test_combine_issues.py`, `python/tests/issue/test_analyze_bugs.py`, `python/tests/issue/test_analyze_issues.py`

### Open questions
- None.
