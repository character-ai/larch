## Decision 1: Float-valued `closure_estimated_tokens` rows
- **Question**: `_parse_snapshot()` silently skips any baseline row where `closure_estimated_tokens` is a float instead of an int. Since the ledger walks full git history by default, how should float-valued rows be handled going forward?
- **Resolution**: Skip the row (unchanged behavior) but print a stderr warning so it is no longer silent. Do not coerce or reject.
- **Source**: user

## Decision 2: Duplicate `skill` keys within one snapshot
- **Question**: `_parse_snapshot()` silently applies last-wins when the same `skill` key appears twice in one baseline revision's JSON array. How should duplicates be handled?
- **Resolution**: Keep last-wins semantics (unchanged behavior) but print a stderr warning so duplicates are no longer silent.
- **Source**: user
