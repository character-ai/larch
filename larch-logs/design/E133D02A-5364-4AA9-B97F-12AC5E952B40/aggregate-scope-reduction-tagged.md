### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_aggregate.py:82-91
- **Concern**: [SCOPE-REDUCTION] FINDING-only aggregate paths must keep level-three-heading ends, not finding-heading. Scenario: `_finding_blocks` and `_count_finding_blocks` call `parse_findings*_text(..., boundary="any_heading")`, so each FINDING block ends at the next non-fenced `###` heading. The plan assigns finding-heading to FINDING-only aggregation, scope split, and count paths. That lets a `### Notes` (or `### OOS_N`) section between FINDING headings get folded into the prior FINDING block, changing scope-split inputs, merge validation, and counts.
- **Proposed resolution**: In `review_aggregate.py`, map `_finding_blocks` / `_count_finding_blocks` to shared FINDING-only parsing with `level-three-heading` end boundaries (or keep the existing `boundary="any_heading"` compatibility alias). Filter `kind == "FINDING"` separately; do not conflate that filter with finding-heading termination.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_aggregate.py:27-87
- **Concern**: [SCOPE-REDUCTION] Mixed `_item_blocks` must stay level-three-heading, not item-heading. Scenario: `_ITEM_BLOCK_RE` segments with `(?=^### |\Z)`, stopping at any level-three heading. The plan assigns item-heading to mixed FINDING+OOS prune/renumber paths. Item-heading would keep intervening `###` sections inside a block until the next canonical FINDING/OOS heading, changing prune/renumber output and mixed-item aggregation.
- **Proposed resolution**: Map `_item_blocks` to shared parsing with `level-three-heading` (plus explicit kind handling). Reserve item-heading for callers whose live contract already ends only at the next canonical FINDING/OOS heading (for example `plan_review_tally._markdown_artifact_blocks`).

### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/audit_runs.py:1080-1091
- **Concern**: [SCOPE-REDUCTION] audit_runs.py is listed for canonical block-parser migration but only uses vote-table and prose-body diagnostic regexes, not reviewer-item block segmentation. Scenario: Including it adds churn without advancing the one-owner goal; prior concern about a missing consumer was based on non-segmentation scans
- **Proposed resolution**: Drop `audit_runs.py` from the firm file set; keep only the existing vote-table and malformed-prose diagnostics local, and document them as lint-exempt distinct grammars if the new detector would match them
