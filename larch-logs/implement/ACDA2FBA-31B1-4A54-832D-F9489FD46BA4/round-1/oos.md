### FINDING_1: [OUT_OF_SCOPE] deviate bullets bypass the lint parser
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-guideline-parser
- **Severity**: major
- **Concern**: `NO_EXCEPTION_DEVIATE_RE` only matches column-0 `- Deviate when:` lines, while the shared guideline parser accepts leading whitespace and spacing variants. That mismatch can let parser-visible `n/a` / `never` deviate bullets escape this lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-guideline-parser: Reuse `_DEVIATE_RE` (or a shared helper exported next to it), match deviate lines the same way the parser does, then apply the `(n/a|never)\b` test to the captured clause text; add a regression test mirroring `test_parse_guideline_entries_omits_bullets_after_non_entry_heading` but with an indented/spaced deviate bullet under a `G-*` entry.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_2: [OUT_OF_SCOPE] duplicate G-* ids need exit-2 test coverage
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-guideline-parser
- **Severity**: minor
- **Concern**: Duplicate `G-*` guideline headings currently fail with `BaselineError`, but there is no pytest coverage for that exit-2 path, so a regression could silently drop the guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-guideline-parser: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] missing baseline file test coverage
- **Reviewer(s)**: dyn-dyn-guideline-parser
- **Severity**: minor
- **Concern**: There is no test for a missing `python/guideline-no-exception-baseline.json`; behavior is fail-closed (exit `2`), but the path is untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-guideline-parser: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

