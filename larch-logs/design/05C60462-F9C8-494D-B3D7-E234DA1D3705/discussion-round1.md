# Discussion Round 1

No user questions were needed; issue #6618 pins scope explicitly. Resolutions below come from the issue text and codebase verification.

## Decision 1: Filter trigger condition
- **Question**: When does the new bug-title filter apply?
- **Resolution**: Only when `request.search == DEFAULT_SEARCH` in `run_prepare`. Any explicit `--search` value passes through unfiltered.
- **Source**: codebase

## Decision 2: No backfill (non-goal)
- **Question**: Should prepare fetch extra issues to reach the requested count after filtering?
- **Resolution**: No. Fetch with the existing `--limit`, filter, keep what remains. Backfill is explicitly out of scope.
- **Source**: codebase

## Decision 3: Hoist with no shims
- **Question**: How do `_bug_title`, `BUG_TITLE_LIFECYCLE_PREFIXES`, and `BUG_PREFIX` become shared?
- **Resolution**: Hoist into a shared module in `python/larch/issue/` with a public `bug_title_match(title: str) -> bool`, preserving semantics exactly. Repoint `analyze_bugs.py` to import from it directly; no re-export shims (docs/python-migration.md).
- **Source**: codebase

## Decision 4: Wire-format change is additive
- **Question**: How does the filter surface in prepare stdout?
- **Resolution**: One new key `ISSUES_FILTERED_NON_BUG=<count>` next to `ISSUES_SELECTED`; `ISSUES_SELECTED` reports the post-filter count. Consumers parse named keys, so this is additive (G-Wire-1).
- **Source**: codebase
