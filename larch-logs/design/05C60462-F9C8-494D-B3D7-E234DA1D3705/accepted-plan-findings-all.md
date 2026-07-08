### FINDING_1:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/learn_from_bugs.py:252-309
- **Concern**: Filtering is keyed only on request.search text, so the implementation cannot tell a user-supplied explicit --search from the default query string.. Scenario: An explicit `learn-from-bugs prepare --search "[BUG] in:title"` will still drop non-bug rows and report a non-zero filtered count, violating the stated "explicit --search queries are unfiltered" contract.
- **Proposed resolution**: Carry an explicit search-origin flag from `prepare_main` into `PrepareRequest` and gate the filter on that flag instead of comparing the query text to DEFAULT_SEARCH.

