### FINDING_1: Preserve OOS eligibility in `count_non_security_blocks`
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-Grammar Migration Auditor, Codex-dyn-Grammar Migration Auditor
- **Severity**: major
- **Concern**: The proposed shared counter would count every non-security `FINDING` and `OOS` block, but existing OOS filing and disposition semantics count only canonical `OOS` blocks and legacy `FINDING` blocks explicitly tagged `[OUT_OF_SCOPE]` or `[OOS]`. Bare in-scope `FINDING` blocks must remain excluded, including in mixed files, or filing and disposition gates will over-count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define `count_non_security_blocks()` as: segment with `parse_blocks()`, keep only OOS kind or FINDING blocks whose title carries an OOS/OUT_OF_SCOPE tag (including trailing-tag legacy forms), then drop security-tagged blocks. Add parity cases in `test_review_types.py` mirroring `test_file_oos.py` legacy/bare-FINDING tests.
  - From Codex-Arch: Preserve the existing OOS eligibility policy in the shared API: count canonical OOS blocks plus legacy FINDING blocks with an explicit `[OUT_OF_SCOPE]` or `[OOS]` tag, while excluding bare FINDING blocks. Add the legacy and bare-header cases to the owner tests.
  - From Cursor-Innovation: Define count_non_security_blocks on OOS-eligible blocks only, preserving legacy tagged-FINDING semantics and bare-FINDING exclusion; add parity cases in python/tests/review/test_review_types.py and keep python/tests/issue/test_file_oos.py green.
  - From Cursor-Pragmatic: Specify count_non_security_blocks() must preserve legacy OOS eligibility (OOS headers plus tagged FINDING only, never bare FINDING) and the file_oos.count_non_security() file gate. Add parity cases to python/tests/review/test_review_types.py
  - From Codex-Pragmatic: Define the shared counter to count OOS blocks plus legacy FINDING blocks tagged OUT_OF_SCOPE or OOS. Preserve the bare-FINDING exclusion and its existing tests.
  - From Cursor-Requirements: Define counting as OOS-kind blocks plus legacy tagged FINDING headers (`[OUT_OF_SCOPE]`/`[OOS]` in the header line only), never bare in-scope FINDING blocks. Add matching cases to python/tests/review/test_review_types.py.
  - From Cursor-dyn-Grammar Migration Auditor: Redefine count_non_security_blocks() to count OOS-eligible blocks only (canonical OOS kind or FINDING header with OOS tag), then apply is_security_block_text(); add parity cases from test_file_oos.py to test_review_types.py.
  - From Codex-dyn-Grammar Migration Auditor: Add an OOS-eligibility mode or predicate to the shared counter. Preserve the existing rule that bare FINDING blocks are not OOS candidates, and cover both tagged and untagged FINDING inputs.


### FINDING_2: Migrate `_finding_dedup_key` consumers
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Requirements, Codex-dyn-Grammar Migration Auditor
- **Severity**: major
- **Concern**: Moving `_finding_dedup_key` to `review_types.py` without updating `plan_review_loop.py` and `plan_review.py` leaves imports or compatibility re-exports pointing at the deleted implementation, causing plan-review import failures or preserving an unintended second owner.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/larch/review/plan_review_loop.py` and `### UPDATED: python/larch/review/plan_review.py` (or an explicit re-export shim) to import `finding_dedup_key` from `review_types`; update tests that still reach the private symbol through `plan_review`.
  - From Codex-Arch: Add both consumers to the firm file list and import `finding_dedup_key` from `review_types.py`. Preserve any intentional external compatibility re-export explicitly, without keeping a second implementation.
  - From Codex-Requirements: Add python/larch/review/plan_review_loop.py and python/larch/review/plan_review.py to the firm migration, importing `finding_dedup_key` from review_types.py directly or preserving an explicitly planned compatibility re-export
  - From Codex-dyn-Grammar Migration Auditor: Update plan_review.py and plan_review_loop.py to import and re-export review_types.finding_dedup_key as required by their existing compatibility surface, or explicitly retain a compatibility alias in plan_review_findings.py and test both import paths.


### FINDING_3: Migrate `compose_review.py`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: `compose_review.py` remains a live canonical `FINDING`/`OOS` heading parser but is absent from the migration list, leaving a second grammar owner and potentially triggering the shared-convention lint ratchet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/larch/review/compose_review.py` to drive artifact parsing from `parse_blocks()` / shared heading helpers (keep synthetic `REJ_*`/`OOS_C_*` IDs local); extend affected tests (`test_compose_review.py`) and lint coverage.
  - From Cursor-Innovation: Add ### UPDATED: python/larch/review/compose_review.py to use shared heading/block helpers with compose-specific policy for rejected headings and historical IDs; extend the testing strategy with python/tests/review/test_compose_review.py.
  - From Cursor-Pragmatic: Add ### UPDATED: python/larch/review/compose_review.py to adopt shared heading/ID helpers; include python/tests/review/test_compose_review.py in the testing strategy


### FINDING_4: Migrate `round_runner.py` consumers
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Pragmatic
- **Severity**: major
- **Concern**: `round_runner.py` imports `_FINDING_RE` and `_OOS_HEADING_RE` from `batch_report.py`. Removing those regexes without migrating this consumer causes import or runtime failures in round filtering and nit counting, while retaining them undermines the sole-owner goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Either add ### UPDATED: python/larch/review/round_runner.py to consume shared review_types heading/OOS-eligibility helpers, or keep batch_report as a thin re-export of the owner helpers until round_runner is migrated.
  - From Cursor-Pragmatic: Add round_runner.py to the firm file set. Replace these imports and uses with review_types operations while preserving preamble, OOS filtering, and interior-heading nit-count behavior. Run the existing round_runner coverage in test_review_and_fix.py.
  - From Cursor-Requirements: Add `### UPDATED: python/larch/review/round_runner.py` to replace `_FINDING_RE`/`_OOS_HEADING_RE` with shared owner helpers (or thin re-exports) and extend python/tests/review/test_review_pipeline.py or round_runner coverage.
  - From Codex-Pragmatic: Add round_runner.py to the firm file set. Replace these imports and uses with review_types operations while preserving preamble, OOS filtering, and interior-heading nit-count behavior. Run the existing round_runner coverage in test_review_and_fix.py.


### FINDING_5: Preserve distinct FINDING-only and mixed-item aggregation paths
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: `review_aggregate.py` has separate FINDING-only and FINDING-plus-OOS segmentation contracts. Replacing both with unfiltered `parse_blocks()` can admit OOS blocks into FINDING-only aggregation, scope splitting, and count paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Spell out in the `review_aggregate` step: use `parse_blocks()` plus explicit `kind` filtering—FINDING-only helpers stay FINDING-only; prune/renumber paths keep FINDING+OOS. Add/keep tests that mixed FINDING+OOS input does not change FINDING-only aggregation counts.


### FINDING_6: Define explicit parser boundary modes
- **Reviewer(s)**: Cursor-dyn-Grammar Migration Auditor, Codex-dyn-Grammar Migration Auditor
- **Severity**: major
- **Concern**: Existing consumers use different block boundaries: some stop at FINDING headings only, some at FINDING/OOS item headings, and some at any unrelated level-three heading. A single implicit `parse_blocks()` boundary can absorb or split content differently and change aggregation, field extraction, classification, deduplication, or rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Grammar Migration Auditor: Keep a FINDING-only finding_heading mode for parse_findings()/parse_findings_text(); use a separate item_heading (FINDING|OOS) mode only where consumers already segment both kinds (_ITEM_BLOCK_RE/_aggregate_oos_blocks paths).
  - From Codex-dyn-Grammar Migration Auditor: Define and document explicit boundary modes on parse_blocks(), map every migrated consumer to its former mode, and add tests with an unrelated level-three heading between canonical items.


### FINDING_7: Preserve `plan_review_tally.py` fallback behavior
- **Reviewer(s)**: Cursor-dyn-Grammar Migration Auditor
- **Severity**: major
- **Concern**: `plan_review_tally.py` currently retains a nonblank normalized chunk when no canonical artifact heading is found. Blindly replacing that behavior with an empty `parse_blocks()` result can alter deduplication and artifact-pool construction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Grammar Migration Auditor: Preserve tally-local behavior: when parse_blocks() is empty and text is non-blank, keep the single-chunk fallback (and preamble chunk split) inside plan_review_tally.py rather than delegating blindly to zero-block semantics.


### FINDING_9: Migrate `core/redact.py` segmentation
- **Reviewer(s)**: Codex-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: `core/redact.py` contains another canonical `FINDING` block-segmentation regex. Leaving it unchanged either violates the one-owner contract or causes the adoption-ratchet lint to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add core/redact.py to the firm migration set and use the shared parser while preserving exact output text and submodule scrub behavior. Include python/tests/core/test_redact.py in affected tests.
  - From Cursor-Requirements: Either migrate scrub_submodule_paths to `parse_blocks()` (FINDING-only) or add an explicit reason-bearing lint suppression if submodule scrubbing is intentionally non-canonical.


### FINDING_10: Migrate `oos_filer.py` security classification
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: `oos_filer.py` uses a copied security classifier tied to private regexes scheduled for removal from `file_oos.py`. Without migration, it may fail at runtime or retain a second security-classification implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add python/larch/issue/oos_filer.py to the firm file set and replace `_is_security_block` with `review_types.is_security_block_text`; include its existing focused test suite in validation


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


