## Proposed Design Outline

### Goals
- Add test coverage for the invalid-`--root` and unresolved-`--since-tag` error paths (`_coerce_root`, `_since_tag_commits`).
- Fix `_build_revisions()` to clear stale `last_values` entries for targets absent from a revision's snapshot, so a reappearing target starts fresh instead of diffing across the gap.
- Make `git.log_path_commits()`'s NUL-delimited split robust to a NUL byte embedded inside a commit subject, instead of hard-failing the whole history walk.
- Add stderr warnings (per user decisions) when `_parse_snapshot()` skips a float-valued `closure_estimated_tokens` row or collapses a duplicate `skill` key via last-wins; behavior itself stays unchanged for both.

### Non-goals
- No change to delta/raise semantics beyond the stale-`last_values` fix.
- No new CLI flags, config keys, or output columns.
- No coercion of float tokens to int, and no rejection of duplicate keys or float rows (per resolved decisions).

### Approach sketch
- All fixes land in `python/larch/lint/skill_closure_ledger.py` and `python/larch/git/git.py`, the two files the review targeted.
- New tests extend the existing suites rather than adding new test files: `python/tests/lint/test_skill_closure_ledger.py` (temp-git-repo + `ledger_main()` pattern already used there) and `python/tests/git/test_git.py` (`StubRunner` pattern already used there).
- Warnings follow the existing `"skill-closure ledger: <msg>"` stderr-prefix convention already used by `_coerce_root`.

### Surfaces in scope
- python/larch/lint/skill_closure_ledger.py
- python/larch/git/git.py
- python/tests/lint/test_skill_closure_ledger.py
- python/tests/git/test_git.py

### Open questions
- None.
