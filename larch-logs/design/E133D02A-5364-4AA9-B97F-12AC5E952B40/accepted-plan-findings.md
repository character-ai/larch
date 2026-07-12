### FINDING_1: Migrate the remaining OOS block segmenter and preserve OOS-only boundaries
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The migration plan leaves `file_oos._parse_oos_blocks` and `_OOS_BLOCK_RE` as a live canonical block-segmentation implementation. These paths are used by filing, issue-cap rollup, and design post-cap flows, so deleting only the counter and classifier regexes would leave a second grammar owner and could change block extraction. The shared parser also needs an OOS-only boundary mode that stops at the next canonical `### OOS_<n>:` heading without splitting on intervening FINDING headings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a fourth documented mode (for example `oos-heading`) that stops only at the next canonical OOS heading, map `file_oos._parse_oos_blocks` and the listed `design_oos` paths to it, and cover mixed FINDING/OOS input in `test_review_types.py`.
  - From Cursor-Innovation: Replace `_parse_oos_blocks` with shared `parse_blocks()` (OOS-only / item-heading as appropriate), or re-export a thin wrapper around the owner. Update `oos_filer.py` and `design_oos.py` call sites in the same change set.
  - From Cursor-Pragmatic: Add an explicit `file_oos.py` step: reimplement `_parse_oos_blocks` as a thin adapter over `review_types.parse_blocks()` with OOS-only `kind` filtering and the same `OosItem` shape; migrate `oos_filer.py` and `design_oos.py` off any remaining private segmentation; add parity coverage in `python/tests/issue/test_oos_filer.py` (and `test_file_oos.py` if present) for multi-block combined text.


### FINDING_2: Scope the adoption-ratchet lint around retained line-level FINDING scans
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The ratchet plan does not distinguish retained single-line FINDING heading scans used for preamble splitting, nit counting, and severity detection from block-segmentation regexes. A literal-heading detector could reject valid migrated code in `round_runner.py` and `review_and_fix.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Limit detection to multiline block-segmentation shapes and/or require reason-bearing suppressions for severity/preamble line scanners; alternatively route those call sites through a shared line-level heading predicate from `review_types.py` and allowlist only that owner API.


### FINDING_4: Migrate `_ground_truth.py` to the shared canonical block parser
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: `_ground_truth.py` is absent from the firm migration list even though `_GT_HEADING_RE` and `_markdown_blocks_by_heading()` parse canonical FINDING/OOS blocks. Leaving it in place violates the one-owner goal and will likely fail the planned shared-convention lint unless it is explicitly exempted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Migrate `_markdown_blocks_by_heading()` to shared `parse_blocks()` with the boundary mode matching today's behavior; add `_ground_truth.py` to the firm file list and extend ground-truth tests (for example in `python/tests/issue/test_analyze_issues.py`) for fenced-heading and mixed-block cases.
  - From Cursor-Requirements: Add `### UPDATED: python/larch/issue/_ground_truth.py`; migrate `_markdown_blocks_by_heading` to shared heading parse plus `parse_blocks()` with the boundary mode that preserves today's per-id title/body extraction
  - From Codex-Requirements: Add `python/larch/issue/_ground_truth.py` to the firm migration set. Replace `_markdown_blocks_by_heading()` segmentation with the shared parser in the matching boundary mode, preserve its dictionary and duplicate-ID behavior, and update its focused ground-truth tests.


### FINDING_5: Preserve `any_heading` compatibility and map it to level-three-heading semantics
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: major
- **Concern**: Existing compatibility APIs accept `boundary="any_heading"` and default to behavior that ends a FINDING block at any level-three Markdown heading. Mapping that value to finding-only or item-only boundaries would change block spans, absorb intervening OOS or unrelated sections, and break aggregation and batch extraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `review_aggregate.py` and `batch_report.py`, document and implement mapping from legacy `any_heading` to owner `level-three-heading` plus `kind == "FINDING"` filtering; add mixed FIXTURE coverage in `python/tests/review/test_review_aggregate.py` with `### OOS_1:` and an unrelated `### Notes:` section between FINDING blocks.
  - From Cursor-Pragmatic: Keep `parse_findings_text` / `parse_findings` signatures unchanged; map `boundary="any_heading"` to fence-aware `level-three-heading` end boundaries and `boundary="finding_heading"` to `finding-heading`; add explicit compatibility tests in `python/tests/review/test_review_types.py`.
  - From Codex-Pragmatic: Keep the current parse_findings() and parse_findings_text() signatures and default. Map finding_heading to the new finding-heading mode and any_heading to the new level-three-heading mode.


### FINDING_6: Add `progress_report.py` to the migration set
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: `progress_report.py` still uses a dynamic heading regex in `_extract_oos_block` to segment canonical reviewer blocks. Omitting it leaves a second block-segmentation owner and bespoke security classification outside the shared grammar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add `### UPDATED: python/larch/report/progress_report.py`; replace `_extract_oos_block` with `review_types.parse_blocks()` (likely `level-three-heading` or item-heading mode matching today's `(?=^### |\Z)` stop) plus `is_security_block_text()`, and extend affected report tests if any exist


### FINDING_7: Explicitly exempt calibration ballot heading grammars
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: The plan discusses exempting voting ballot heading regexes but does not address the parallel ballot parsers in `calibration_replay.py`. The ratchet could flag these distinct historical-ballot grammars or force canonical-only IDs that break production-parity replay.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: State explicitly that calibration ballot heading matchers are retained distinct grammar like `voting.py` ballot parsing, and ensure `lint_shared_convention_regex.py` excludes ballot-rebuild patterns (or add a reason-bearing suppression path) without forcing canonical-only ids


### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_aggregate.py:82-91
- **Concern**: [SCOPE-REDUCTION] FINDING-only aggregate paths must keep level-three-heading ends, not finding-heading. Scenario: `_finding_blocks` and `_count_finding_blocks` call `parse_findings*_text(..., boundary="any_heading")`, so each FINDING block ends at the next non-fenced `###` heading. The plan assigns finding-heading to FINDING-only aggregation, scope split, and count paths. That lets a `### Notes` (or `### OOS_N`) section between FINDING headings get folded into the prior FINDING block, changing scope-split inputs, merge validation, and counts.
- **Proposed resolution**: In `review_aggregate.py`, map `_finding_blocks` / `_count_finding_blocks` to shared FINDING-only parsing with `level-three-heading` end boundaries (or keep the existing `boundary="any_heading"` compatibility alias). Filter `kind == "FINDING"` separately; do not conflate that filter with finding-heading termination.


### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_aggregate.py:27-87
- **Concern**: [SCOPE-REDUCTION] Mixed `_item_blocks` must stay level-three-heading, not item-heading. Scenario: `_ITEM_BLOCK_RE` segments with `(?=^### |\Z)`, stopping at any level-three heading. The plan assigns item-heading to mixed FINDING+OOS prune/renumber paths. Item-heading would keep intervening `###` sections inside a block until the next canonical FINDING/OOS heading, changing prune/renumber output and mixed-item aggregation.
- **Proposed resolution**: Map `_item_blocks` to shared parsing with `level-three-heading` (plus explicit kind handling). Reserve item-heading for callers whose live contract already ends only at the next canonical FINDING/OOS heading (for example `plan_review_tally._markdown_artifact_blocks`).


