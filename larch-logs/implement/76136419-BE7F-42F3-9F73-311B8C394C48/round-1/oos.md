### FINDING_1: [OUT_OF_SCOPE] Invariant heading-depth bounds differ between coverage indexer and reader
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, cursor-specialist-plan-fidelity-auto
- **Severity**: minor
- **Concern**: Invariant heading-depth bounds still differ between `learn_from_bugs.coverage_index` (`_INVARIANT_ID_RE` requires `#{2,4}` headings at `python/larch/issue/learn_from_bugs.py:64`) and `parse_invariant_entries` (`_INVARIANT_HEADING_RE` accepts `#{1,6}` at `python/larch/core/architectural_guidelines.py:55`). A repo with only `# I-*` or `#####`/`######` `I-*` headings is surfaced to `/design` and `/implement` via `read_invariants` but omitted from learn-from-bugs coverage indexing, so dedup can disagree with design/implement invariant surfacing and may propose coverage that already exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From cursor-specialist-plan-fidelity-auto: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_2: [OUT_OF_SCOPE] Cross-parser test guard checks only first parse line
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The cross-parser guard in `python/tests/issue/test_learn_from_bugs.py:172` only inspects the first split line of `parse_invariant_entries()` output instead of the full normalized output, and does not assert `read_invariants()` status/content. A future parse change that emits spurious non-heading lines could still pass the first-line slice check, and a regression in `read_invariants()` wiring could slip past while `parse_invariant_entries()` still passes the heading-line check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_3: [OUT_OF_SCOPE] Invariant ID regex duplicated across modules
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Invariant ID grammar is duplicated as separate regex literals (`_INVARIANT_ID_RE` in `python/larch/issue/learn_from_bugs.py:64` and `_INVARIANT_HEADING_RE` in `python/larch/core/architectural_guidelines.py:55`) instead of one shared constant. Future edits can reintroduce INV-* vs I-* or hyphen-shape drift despite the new regression test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

