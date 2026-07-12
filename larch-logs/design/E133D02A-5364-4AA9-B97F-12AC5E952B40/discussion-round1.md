## Decision 1: Grammar module location
- **Question**: Where should the FINDING/OOS block-grammar owner live?
- **Resolution**: Grow `larch/review/review_types.py` — no new file; consumers already import from it.
- **Source**: user

## Decision 2: Dedup identity function
- **Question**: Should `_finding_dedup_key` (Location+Concern field extraction) move to the grammar owner?
- **Resolution**: Yes — move to `review_types.py` and make it public as `finding_dedup_key`.
- **Source**: user

## Decision 3: Heading depth normalization
- **Question**: `rejected_analysis.py` uses `#{1,6}` while all others require `###`. Standardize?
- **Resolution**: Yes — standardize to `###` in the grammar owner; the lenient match is almost certainly a bug.
- **Source**: user

## Decision 4: Non-security counting scope
- **Question**: Are `_count_non_security_markdown` (file_oos.py) and `count_non_security_oos_blocks` (oos_disposition.py) in scope?
- **Resolution**: Yes — both implement the same block-segmentation+is_security logic. A single `count_non_security_blocks(text)` helper in `review_types.py` replaces both.
- **Source**: codebase

## Decision 5: Lint ratchet placement
- **Question**: Extend `lint_shared_convention_regex.py` or add a new lint module?
- **Resolution**: Extend `lint_shared_convention_regex.py` — it already detects duplicate convention regexes and uses the same AST-scan pattern. Add a `_looks_like_finding_block_heading_regex` check there.
- **Source**: codebase
