## Proposed Design Outline

### Goals
- Default-search `/learn-from-bugs` prepare selects only `[BUG]`-titled issues (lifecycle prefixes tolerated).
- Share one bug-title normalizer between `/analyze-bugs` and `/learn-from-bugs`.
- Report dropped rows via a new additive `ISSUES_FILTERED_NON_BUG=<count>` stdout key.

### Non-goals
- No backfill to reach the requested count after filtering.
- No filtering for explicit `--search` values.
- No behavior change for `/analyze-bugs` beyond the import repoint.

### Approach sketch
- Hoist `_bug_title`, `BUG_TITLE_LIFECYCLE_PREFIXES`, `BUG_PREFIX` into new `python/larch/issue/title_match.py`; public name `bug_title_match`, semantics byte-identical.
- Repoint `analyze_bugs.py` to import from the shared module; no shims.
- In `run_prepare`, filter `list_issues` output by `bug_title_match` only when `request.search == DEFAULT_SEARCH`; count drops.
- Add `ISSUES_FILTERED_NON_BUG` to the stats dict next to `ISSUES_SELECTED`.
- Document the new key in `skills/learn-from-bugs/SKILL.md` Step 2.

### Surfaces in scope
- `python/larch/issue/title_match.py` (new), `analyze_bugs.py`, `learn_from_bugs.py`
- `python/tests/issue/test_learn_from_bugs.py`, `skills/learn-from-bugs/SKILL.md`

### Open questions
- None.
