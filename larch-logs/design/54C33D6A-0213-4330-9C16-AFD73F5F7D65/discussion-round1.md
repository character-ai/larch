## Decision 1: Remaining voter-calibration.py raw-argv gap
- **Question**: Is the `_run_gh_json(["gh", "issue", "view", ...])` call in `skills/voter-calibration/scripts/voter-calibration.py:202` in scope for this umbrella?
- **Resolution**: Yes. The original issue #7007 explicitly listed `voter-calibration.py:175` as a site to fix. The bulk issue-list call was fixed (now uses `fetch_main` → `gh.issue_list_read`), but the `gh issue view` call at line ~202 was missed by child #7053. Fix by replacing `_run_gh_json(["gh", "issue", "view", ...])` with `gh.issue_view_field_read(proc, ...)` using the already-imported `larch.core.proc` module as the Runner. Delete `_run_gh_json` (only used once).
- **Source**: codebase

## Decision 2: Lint scope extension (skills/)
- **Question**: Should the `gh-argv-literal` lint be extended to cover `skills/` Python files?
- **Resolution**: Out of scope. `iter_source_files` scanning `python/` only was the intentional design of #7055. Extending lint scope to `skills/` is a new issue if desired.
- **Source**: codebase
