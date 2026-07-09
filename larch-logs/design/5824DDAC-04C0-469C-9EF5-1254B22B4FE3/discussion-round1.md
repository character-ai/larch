## Decision 1: Fix direction — narrow indexer vs. widen reader
- **Question**: Should `_INVARIANT_ID_RE` be narrowed to `I-*` only, or should `_INVARIANT_HEADING_RE` be widened to accept `INV-*`?
- **Resolution**: Narrow `_INVARIANT_ID_RE`. Every existing invariant, every test fixture, and the reader all use `I-*`. The `INV|` alternation in the indexer was introduced in #6465 and appears to be an oversight; no doc or invariant in the repo uses `INV-*`.
- **Source**: codebase
