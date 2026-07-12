### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/review/review_types.py
- **Concern**: The three documented boundary modes omit the OOS-only segmentation contract used by filing helpers.. Scenario: `file_oos._parse_oos_blocks` and `design_oos` OOS-only paths end blocks at the next `### OOS_<n>:` only (`file_oos.py:228`, `design_oos.py:88-94`, `design_oos.py:494-499`). `item-heading` or `level-three-heading` would split at intervening `### FINDING_<n>:` lines and change issue-cap rollup, URL annotation, and unfiled-block extraction.
- **Proposed resolution**: Add a fourth documented mode (for example `oos-heading`) that stops only at the next canonical OOS heading, map `file_oos._parse_oos_blocks` and the listed `design_oos` paths to it, and cover mixed FINDING/OOS input in `test_review_types.py`.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/file_oos.py
- **Concern**: The `file_oos.py` migration names only the non-security counter and security classifier, not `_parse_oos_blocks`.. Scenario: `_OOS_BLOCK_RE` and `_parse_oos_blocks` (`file_oos.py:228-231`, `679-681`, `786`) remain a live canonical block segmenter on the issue-cap path. Removing header/counter regexes without migrating this helper leaves a second grammar owner and can fail the adoption ratchet or break `issue_cap`.
- **Proposed resolution**: Extend the `file_oos.py` step to replace `_parse_oos_blocks` with shared `parse_blocks()` using the OOS-only boundary mode, then delete `_OOS_BLOCK_RE`; add parity coverage in `test_file_oos.py` or `test_review_types.py`.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/lint/lint_shared_convention_regex.py
- **Concern**: The ratchet plan does not carve out retained single-line FINDING header scans that are not block segmentation.. Scenario: `round_runner.py` and `review_and_fix.py` keep module-level or inline `^### FINDING_[0-9]+:` patterns for preamble split, nit counting, and high-severity detection (`round_runner.py:146-193`, `review_and_fix.py:129-137`). A detector that flags any canonical heading literal will fail `python3 python/cli.py lint shared-convention-regex` after those modules are otherwise migrated.
- **Proposed resolution**: Limit detection to multiline block-segmentation shapes and/or require reason-bearing suppressions for severity/preamble line scanners; alternatively route those call sites through a shared line-level heading predicate from `review_types.py` and allowlist only that owner API.



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



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/issue/file_oos.py:228-680
- **Concern**: Migrate `file_oos._parse_oos_blocks` / `_OOS_BLOCK_RE`, not only the counter and classifier. Scenario: The plan updates `file_oos.py` for `_count_non_security_markdown` and security classification only. `_OOS_BLOCK_RE` and `_parse_oos_blocks` remain a second live block segmenter used by `oos_filer.py`, `design_oos.py`, and filing/rollup paths. The new shared-convention lint will flag this regex, and the one-owner goal stays incomplete.
- **Proposed resolution**: Replace `_parse_oos_blocks` with shared `parse_blocks()` (OOS-only / item-heading as appropriate), or re-export a thin wrapper around the owner. Update `oos_filer.py` and `design_oos.py` call sites in the same change set.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/review_phase_detail.py:18-20
- **Concern**: Preserve lenient rejected-OOS IDs when swapping the block regex. Scenario: `_REJECTED_OOS_BLOCK_RE` accepts `(?:OOS|FINDING)_[0-9A-Za-z_]+`. The canonical owner allows only numeric `FINDING_<digits>` / `OOS_<digits>`. Blind migration drops historical rejected-OOS blocks whose headings use wider IDs, shrinking final-report rejected-OOS audit output.
- **Proposed resolution**: Either keep a local malformed/historical-ID matcher with a reason-bearing lint suppression for this diagnostic path, or extend the migration note to use a compose/historical boundary mode that still accepts alphanumeric IDs for rejected-OOS audit only.



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/file_oos.py:228-681
- **Concern**: Migrate `file_oos._parse_oos_blocks` / `_OOS_BLOCK_RE`, not only the counter and security helpers. Scenario: The plan updates `_count_non_security_markdown` and security regexes but leaves `_OOS_BLOCK_RE` and `_parse_oos_blocks`, which still segment canonical `### OOS_<n>:` blocks. `oos_filer.py`, `design_oos._parse_post_cap_combined_blocks`, and issue-cap logic depend on this API; the new shared-convention lint will also flag the literal `_OOS_BLOCK_RE`. A partial `file_oos.py` migration keeps a second block owner and can break filer or design post-cap flows when regexes are deleted elsewhere.
- **Proposed resolution**: Add an explicit `file_oos.py` step: reimplement `_parse_oos_blocks` as a thin adapter over `review_types.parse_blocks()` with OOS-only `kind` filtering and the same `OosItem` shape; migrate `oos_filer.py` and `design_oos.py` off any remaining private segmentation; add parity coverage in `python/tests/issue/test_oos_filer.py` (and `test_file_oos.py` if present) for multi-block combined text.



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/issue/_ground_truth.py:216-408
- **Concern**: Add `_ground_truth.py` to the migration list. Scenario: `_GT_HEADING_RE` and `_markdown_blocks_by_heading()` still parse canonical `### FINDING_<n>:` / `### OOS_<n>:` blocks outside `review_types.py`. The planned lint ratchet scans `python/larch/**/*.py`, so this surviving copy can fail `python3 python/cli.py lint shared-convention-regex` and leaves the one-owner goal incomplete.
- **Proposed resolution**: Migrate `_markdown_blocks_by_heading()` to shared `parse_blocks()` with the boundary mode matching today's behavior; add `_ground_truth.py` to the firm file list and extend ground-truth tests (for example in `python/tests/issue/test_analyze_issues.py`) for fenced-heading and mixed-block cases.



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_aggregate.py:82-91
- **Concern**: Pin `boundary="any_heading"` callers to `level-three-heading`, not `finding-heading` or `item-heading`. Scenario: `_finding_blocks`, `_count_finding_blocks`, `batch_report._extract_finding_block`, and `_finding_id_from_block` use `parse_findings_text(..., boundary="any_heading")`, which ends each FINDING block at the next `###` heading. `finding-heading` would absorb intervening `### OOS_<n>:` or unrelated `###` sections into FINDING bodies; `item-heading` still differs for non-item headings. Wrong mode mapping breaks FINDING-only aggregation, scope splitting, and skipped-finding extraction.
- **Proposed resolution**: In `review_aggregate.py` and `batch_report.py`, document and implement mapping from legacy `any_heading` to owner `level-three-heading` plus `kind == "FINDING"` filtering; add mixed FIXTURE coverage in `python/tests/review/test_review_aggregate.py` with `### OOS_1:` and an unrelated `### Notes:` section between FINDING blocks.



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_types.py:76-111
- **Concern**: Preserve the public `boundary="any_heading"` compatibility contract. Scenario: Step 1 says compatibility parsers use "finding-heading semantics", but the live API defaults to `boundary="any_heading"` and several callers rely on it. Reimplementing compatibility through finding-heading-only boundaries would change block spans and break aggregation and batch extraction without any test signal.
- **Proposed resolution**: Keep `parse_findings_text` / `parse_findings` signatures unchanged; map `boundary="any_heading"` to fence-aware `level-three-heading` end boundaries and `boundary="finding_heading"` to `finding-heading`; add explicit compatibility tests in `python/tests/review/test_review_types.py`.



### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_types.py:82-112
- **Concern**: The planned compatibility wrappers must preserve their existing boundary argument and default, not force finding-heading semantics. Scenario: Existing callers can pass boundary="any_heading", and the default currently stops a FINDING block at any level-three heading. Removing that value or default silently absorbs later Markdown sections or raises ValueError for existing callers.
- **Proposed resolution**: Keep the current parse_findings() and parse_findings_text() signatures and default. Map finding_heading to the new finding-heading mode and any_heading to the new level-three-heading mode.



### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/report/progress_report.py:1389-1401
- **Concern**: progress_report.py is absent from the firm migration list but still segments canonical reviewer blocks via a dynamic `^### {id}:` regex in `_extract_oos_block`. Scenario: After the adoption ratchet lands, this live `python/larch` consumer remains a second block-segmentation owner and `_adjust_design_security_oos` will keep bespoke boundary logic instead of the shared parser and security classifier
- **Proposed resolution**: Add `### UPDATED: python/larch/report/progress_report.py`; replace `_extract_oos_block` with `review_types.parse_blocks()` (likely `level-three-heading` or item-heading mode matching today's `(?=^### |\Z)` stop) plus `is_security_block_text()`, and extend affected report tests if any exist



### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/issue/_ground_truth.py:216-408
- **Concern**: _ground_truth.py is absent from the firm migration list but `_GT_HEADING_RE` still parses and segments canonical `### FINDING|OOS_<digits>:` blocks for `_markdown_blocks_by_heading`. Scenario: Ground-truth ingestion keeps a duplicate grammar owner under `python/larch`, and the new shared-convention lint will flag this regex unless it is migrated or explicitly exempted
- **Proposed resolution**: Add `### UPDATED: python/larch/issue/_ground_truth.py`; migrate `_markdown_blocks_by_heading` to shared heading parse plus `parse_blocks()` with the boundary mode that preserves today's per-id title/body extraction



### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/audit_runs.py:1080-1091
- **Concern**: [SCOPE-REDUCTION] audit_runs.py is listed for canonical block-parser migration but only uses vote-table and prose-body diagnostic regexes, not reviewer-item block segmentation. Scenario: Including it adds churn without advancing the one-owner goal; prior concern about a missing consumer was based on non-segmentation scans
- **Proposed resolution**: Drop `audit_runs.py` from the firm file set; keep only the existing vote-table and malformed-prose diagnostics local, and document them as lint-exempt distinct grammars if the new detector would match them



### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/calibration/calibration_replay.py:35-36
- **Concern**: The plan exempts voting ballot heading regexes from reviewer-item migration but does not name calibration_replay's parallel `_BALLOT_HEADING_RE` / `_ANY_BALLOT_HEADING_RE` parsers. Scenario: The adoption ratchet may flag calibration ballot rebuild regexes or pressure a canonical-ID migration that breaks production-parity replay of historical ballots with non-numeric ids
- **Proposed resolution**: State explicitly that calibration ballot heading matchers are retained distinct grammar like `voting.py` ballot parsing, and ensure `lint_shared_convention_regex.py` excludes ballot-rebuild patterns (or add a reason-bearing suppression path) without forcing canonical-only ids



### FINDING_17:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/issue/_ground_truth.py:216,402-409
- **Concern**: Migrate the live `_GT_HEADING_RE` block parser. Scenario: The plan adds a lint for module-level canonical heading regexes but omits this parser. The proposed lint will fail on `_GT_HEADING_RE`, or suppressing it would leave a second canonical segmentation owner and violate the feature goal.
- **Proposed resolution**: Add `python/larch/issue/_ground_truth.py` to the firm migration set. Replace `_markdown_blocks_by_heading()` segmentation with the shared parser in the matching boundary mode, preserve its dictionary and duplicate-ID behavior, and update its focused ground-truth tests.



