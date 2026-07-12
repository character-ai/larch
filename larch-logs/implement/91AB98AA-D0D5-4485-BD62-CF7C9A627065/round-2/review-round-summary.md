# Review Round 2

- Mode: `diff`
- 4 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Missing mixed OOS/FINDING/OOS adapter regression test
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: `test_file_oos.py` lacks the plan-required `_parse_oos_blocks` regression test for `OOS_1` followed by an intervening `FINDING_2` and then `OOS_3`. A boundary regression could merge or drop content without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_10: Rejected-findings paths still use the wrong block boundary
- **Reviewer(s)**: dyn-dyn-boundary-modes
- **Severity**: major
- **Concern**: `_rejected_dedup_keys()` and `_filter_rejected_findings_body_canonical()` still use `boundary="finding-heading"`, causing an intervening OOS block to be absorbed into the preceding FINDING block's body and deduplication material.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-boundary-modes: Address the concern above.


### FINDING_11: Scrubbing drops canonical OOS sections
- **Reviewer(s)**: dyn-dyn-boundary-modes
- **Severity**: major
- **Concern**: `scrub_submodule_paths()` reconstructs output from the preamble and kept FINDING blocks only, dropping standalone OOS sections and other non-FINDING spans even when they should be preserved unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-boundary-modes: Address the concern above.


### FINDING_12: Plain-URL recovery can rewrite across an intervening FINDING
- **Reviewer(s)**: dyn-dyn-boundary-modes
- **Severity**: major
- **Concern**: `_recover_accepted_from_sentinel()` uses `boundary="oos-heading"` for URL injection. With `OOS_1 / FINDING_2 / OOS_3`, the first OOS span can include the intervening FINDING and sibling content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-boundary-modes: Address the concern above.
