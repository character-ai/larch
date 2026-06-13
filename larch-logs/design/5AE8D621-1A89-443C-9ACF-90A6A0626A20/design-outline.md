## Proposed Design Outline

### Goals
- Fix stale `release-prepare.sh` references in `classify-bump.md` (lines 7, 12, and the file title).
- Extend `migration_lint.py` to catch bare basename occurrences in markdown prose.
- Consolidate verify-main comparison logic so `finalize.py` and `verify_main.py` share one implementation.

### Non-goals
- Items 2 and 4 are already fixed; do not re-implement them.
- No changes to the lint tool's exclusion list or manifest format.
- No changes to any `/implement` or `/design` skill surface.

### Approach sketch
- Update `classify-bump.md` title and lines 7/12 to reference `python/cli.py release classify-bump` and `python/cli.py release prepare`.
- Add a bare-basename check in `_line_references_retired()` in `migration_lint.py`; limit to a `# lint-ignore` escape hatch for legitimate historical prose.
- Extract a `_title_matches(actual, expected, pr_number)` helper in `finalize.py`; update the inline block to call it; have `verify_main.py` import and use it.

### Surfaces in scope
- `.claude/skills/release/scripts/classify-bump.md`
- `python/migration_lint.py`
- `python/finalize.py`
- `python/verify_main.py`
- `python/test_migration_lint.py` (new tests for baseline matching)
- `python/test_finalize.py` or equivalent (update tests for shared helper)

### Open questions
- Should the baseline-matching exemption use an inline comment (`# lint-ignore`) or a dedicated exclusion list?
