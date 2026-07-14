### FINDING_1: [OUT_OF_SCOPE] Step 4 noop breadcrumb stream
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The Step 4 noop breadcrumb moved to stderr, outside Piece 2’s firm headings; this is unrelated to the baseline-engine review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: None for this feature; keep it separate from baseline engine review.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_2: [OUT_OF_SCOPE] Scan-only finding deduplication
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Scan-only deduplication still keys only on path, line, rule, and message, potentially collapsing distinct symbol-metric findings; this predates the branch and is outside scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: None in this piece; baseline-active mode already uses symbol identity via `_project_findings`.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_10: [OUT_OF_SCOPE] Scan-path validation does not cover baseline parsing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Scan-path finding validation exercises a different code path from baseline-file parsing and is not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add baseline-file parse tests as in-scope finding above not here.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
