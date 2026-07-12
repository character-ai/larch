### FINDING_2: [OUT_OF_SCOPE] Divergent fluff-analysis heading parser
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `skills/fluff-analysis/scripts/fluff-analysis.py` retains a separate FINDING/OOS/REJ parser outside `review_types`, allowing historical-log parsing to diverge from the canonical grammar without the Python lint ratchet detecting it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_3: [OUT_OF_SCOPE] Duplicate OOS heading parser in issue creation
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: `python/larch/issue/issue_create.py` retains a duplicate `OOS_HEADING_RE`, so issue-creation heading semantics can drift from `review_types`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Uncovered fence handling in rejected-analysis heading detection
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `_first_canonical_heading` is not fence-aware, so fenced example headings in `prose_body` may be mistaken for the first canonical heading during rejected-analysis ingest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_6: [OUT_OF_SCOPE] Dead security-focus regex remains
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The unused `_SECURITY_FOCUS_RE` remains after security classification centralization, leaving a possible second classifier for future edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_13: [OUT_OF_SCOPE] Missing adapter parity coverage
- **Reviewer(s)**: dyn-dyn-boundary-modes
- **Severity**: minor
- **Concern**: `test_file_oos.py` still lacks mixed `OOS/FINDING/OOS` coverage for `_parse_oos_blocks()`, despite the earlier plan requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-boundary-modes: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_14: [OUT_OF_SCOPE] Synthetic and historical FINDING grammars remain local
- **Reviewer(s)**: dyn-dyn-boundary-modes
- **Severity**: minor
- **Concern**: `compose_review.py` still uses local alphanumeric matchers for synthetic or historical IDs. This is consistent with the distinct-grammar carve-out, but remains outside canonical numeric heading parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-boundary-modes: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_15: [OUT_OF_SCOPE] Audit diagnostics retain a local FINDING regex
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `audit_runs.py` still uses a local FINDING heading regex for `rej-category-blank` diagnostics, leaving a pre-existing potential for drift from canonical heading rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
