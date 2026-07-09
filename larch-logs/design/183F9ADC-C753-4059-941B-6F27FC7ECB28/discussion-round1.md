## Decision 1: New lint convention-table breadth
- **Question**: Should `lint_shared_convention_regex` cover both the ID-heading grammar and the `[BUG]` bug-title predicate, or only the ID-heading grammar this bug fixes?
- **Resolution**: Cover both conventions, as written in work item 5. Convention (a) ID-heading grammar, owner `python/larch/core/architectural_guidelines.py`. Convention (b) `[BUG]` bug-title predicate, owner `python/larch/issue/title_match.py`. The new lint must skip lifecycle prefixes already flagged by `lint_lifecycle_prefix_literal` rather than double-report.
- **Source**: user

## Decision 2: Reader grammar is canonical; do not widen
- **Question**: Which grammar becomes the single source when the reader and indexer are merged?
- **Resolution**: Keep the reader's current acceptance: guidelines exactly `###` with hyphenated areas allowed (`G-[A-Za-z0-9-]+-\d+`); invariants `#{1,6}` (`I-[A-Za-z0-9-]+-\d+`). Repoint the indexer to the shared reader constants. Do not widen the reader. `INV-*` stays rejected everywhere.
- **Source**: issue (work item 3 + acceptance criteria)

## Decision 3: Landing baseline
- **Question**: Empty baseline with a hard ban, or grandfathered baseline?
- **Resolution**: Work items 1-2 (fix) and work item 5 (lint) land together in one change, so land with an empty baseline and a hard ban. No grandfathering.
- **Source**: issue (work item 6)

## Hard constraints (must not break)
- Every entry currently in `ARCHITECTURAL_GUIDELINES.md` and `ARCHITECTURAL_INVARIANTS.md` parses to the identical (id, title) set before and after.
- `bug_title_match` semantics unchanged.
- Adding `re.MULTILINE` must not change the reader's per-line `.match` behavior.
- Layering: `larch.core` sits below `larch.issue`; `learn_from_bugs` importing shared constants from `larch.core.architectural_guidelines` must pass `lint_layering`.
