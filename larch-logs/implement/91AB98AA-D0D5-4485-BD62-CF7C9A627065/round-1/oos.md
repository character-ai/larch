### FINDING_10: [OUT_OF_SCOPE] fluff-analysis retains a divergent canonical block parser
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-boundary-modes
- **Severity**: major
- **Concern**: `fluff-analysis` still uses its own `HEAD_RE`/`parse_md_blocks()` grammar for FINDING/OOS/REJ segmentation, allowing heading depth and ID behavior to diverge from the shared canonical parser. This was distinguished by reviewers as outside the current diff scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-boundary-modes: - **[OUT_OF_SCOPE]** `skills/fluff-analysis/scripts/fluff-analysis.py:236-257` — The plan called for migrating canonical reviewer-item segmentation to `review_types`, but this script still owns `HEAD_RE` / `parse_md_blocks()` with a distinct `#{2,4}` historical grammar. That leaves a second live parser outside the owner and outside the adoption ratchet.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_11: [OUT_OF_SCOPE] audit_runs retains local FINDING heading scanning
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-boundary-modes
- **Severity**: minor
- **Concern**: `audit_runs.py` still uses hand-written FINDING heading regexes for category extraction rather than shared canonical segmentation. Reviewers distinguished this as outside the current diff scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-boundary-modes: - **[OUT_OF_SCOPE]** `python/larch/issue/audit_runs.py` — No `review_types.parse_blocks` migration appears in the branch diff despite the plan listing `audit_runs.py` as in scope, so any canonical FINDING/OOS segmentation there remains on legacy regex paths.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_12: [OUT_OF_SCOPE] rejected-analysis heading detection is not fence-aware
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `_first_canonical_heading` scans lines without fence awareness, so heading-like prose inside fenced bodies may be mistaken for the first canonical finding heading during rejected-analysis ingest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_13: [OUT_OF_SCOPE] issue creation retains a duplicate OOS heading parser
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `issue_create.py` retains `OOS_HEADING_RE` as a separate OOS heading parser outside `review_types`. Reviewers identified this as pre-existing and outside the current plan scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_14: [OUT_OF_SCOPE] calibration replay intentionally retains distinct heading grammar
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Calibration ballot heading regexes remain local by design for historical grammar and are not a migration gap introduced by this change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_15: [OUT_OF_SCOPE] review tally duplicates OOS-only counting policy
- **Reviewer(s)**: dyn-dyn-boundary-modes
- **Severity**: minor
- **Concern**: `_non_security_oos_count` reimplements OOS-only counting instead of using the shared counting policy, so tagged legacy OOS findings may diverge from filing and disposition counters. Reviewers identified this as consistency debt outside the current boundary-mode regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-boundary-modes: - **[OUT_OF_SCOPE]** `python/larch/review/review_tally.py:1237-1257` — `_non_security_oos_count` reimplements OOS-only counting with `oos-heading` plus `block.startswith("### OOS_")` instead of the shared `count_non_security_blocks()` policy, so tagged legacy `### FINDING_N: [OUT_OF_SCOPE]` rows on OOS paths stay out of sync with filing/disposition counters. Behavior matches the pre-migration `re.split` on `### OOS_` only; this is consistency debt, not a boundary-mode regression introduced here.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_16: [OUT_OF_SCOPE] compose_review retains local synthetic heading matchers
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `compose_review` retains local alphanumeric FINDING/OOS heading matchers for synthetic or rejected IDs. Reviewers distinguished these compose-specific IDs as an intentionally distinct grammar outside the current diff scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
