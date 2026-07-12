## Goal
Implement issue #7001: [IMPLEMENTING] contract-unification [FEATURE] One FINDING/OOS block-grammar owner.

## Implementation Plan
## Plan

## Approach

1. Make `larch.review.review_types` the sole owner of canonical reviewer-item grammar and shared policy.
   - Add a frozen parsed-block value type containing the canonical item ID, item kind (`FINDING` or `OOS`), title/header text, full block text, and source span or equivalent data needed by consumers that preserve exact rendered text.
   - Add shared canonical-heading operations for parsing and validating exactly `### FINDING_<digits>:` and `### OOS_<digits>:` headings, plus a line-level canonical-heading predicate/matcher for callers that only need to inspect a heading. Canonical parsing must require uppercase kinds, numeric IDs, and exactly three heading hashes.
   - Ignore apparent canonical headings within fenced code blocks.
   - Keep malformed-heading recognition out of the canonical parser so callers that deliberately diagnose malformed output can retain separate validation regexes.
   - Keep `parse_findings()` and `parse_findings_text()` as compatibility APIs backed by the owner, preserving their public return shapes and FINDING-only behavior. Preserve existing signatures and boundary compatibility: `boundary="finding_heading"` maps to `finding-heading`; `boundary="any_heading"` maps to `level-three-heading`; preserve the current default.

2. Define explicit block-boundary modes rather than giving `parse_blocks()` one implicit segmentation contract.
   - Provide documented modes for:
     - **finding-heading**: a FINDING block ends at the next canonical FINDING heading.
     - **oos-heading**: an OOS block ends at the next canonical OOS heading, without splitting on intervening canonical FINDING headings.
     - **item-heading**: a canonical item block ends at the next canonical FINDING or OOS heading.
     - **level-three-heading**: a canonical item block ends at any non-fenced `###` heading, preserving callers that deliberately exclude subsequent unrelated Markdown sections.
   - Map every migrated caller to the mode matching its current contract. Do not infer termination semantics from a `kind` filter: FINDING-only or OOS-only selection remains separate from the boundary mode.
   - Preserve preamble handling locally where a caller currently retains it rather than treating an empty parsed-block result as equivalent to empty input.

3. Centralize security and OOS-eligibility policy in `review_types.py`.
   - Move the current security classifier into `is_security_block_text()`, preserving recognition of explicit security header tags, `focus-area=security`, and focus-area fields; case-insensitive matching; and the current treatment of fenced and inline-code examples.
   - Keep failure-sensitive callers responsible for fail-closed handling when the classifier result is not a boolean.
   - Add an OOS-eligibility predicate for canonical blocks:
     - canonical `OOS` blocks are eligible;
     - legacy `FINDING` blocks are eligible only when their header carries an explicit `[OUT_OF_SCOPE]` or `[OOS]` tag, including supported trailing-tag forms;
     - bare `FINDING` blocks are never OOS-eligible.
   - Define `count_non_security_blocks(text)` as the existing OOS filing/disposition counter semantics: parse canonical blocks with the appropriate item-boundary mode, retain only OOS-eligible blocks, then exclude security-tagged blocks. It must not count ordinary in-scope FINDING blocks.

4. Move `_finding_dedup_key` unchanged into `review_types.py` as public `finding_dedup_key`.
   - Preserve Location and Concern extraction, normalization, and fallback behavior exactly.
   - Replace private imports and duplicate implementations with the owner helper.
   - Preserve an explicit compatibility alias only where current imports or tests require it; do not retain a second implementation.

5. Migrate every in-scope grammar, segmentation, security, counter, and dedup consumer.
   - Replace canonical heading parsing and block segmentation with the shared parser or line-level owner operation, using the caller’s documented boundary mode.
   - Filter parsed blocks explicitly by `kind` wherever a caller formerly accepted only FINDING or only OOS blocks.
   - Retain regexes only for distinct grammars: vote rows, calibration ballots, generated output, field extraction, historical/synthetic IDs, and deliberate malformed-heading diagnostics.
   - Preserve exact output, whitespace, trailing-newline, ordering, preamble, duplicate-ID, and caller-specific validation behavior when adapting consumers.

6. Extend the shared-convention lint as an adoption ratchet without banning legitimate retained line-level scans.
   - Detect literal regexes that perform canonical FINDING/OOS Markdown **block segmentation** or duplicate canonical heading parsing outside `review_types.py`.
   - Cover supported direct `re` calls and module-level pattern assignments, not solely `re.compile`.
   - Do not flag distinct line-level logic that has been migrated to the owner line-heading operation. For any justified retained line-level canonical scan, require the existing reason-bearing suppression mechanism.
   - Keep matching narrow enough to permit vote syntax, calibration ballot-rebuild syntax, synthetic/generated headings, field-label extraction, classification IDs, and explicit malformed-input diagnostics.
   - Permit intentional exceptions only through existing reason-bearing suppressions.
   - Add coverage for every migrated formerly-live parser so removing local regex definitions cannot leave stale imports or an unowned grammar copy.

## Files to modify/create

### UPDATED: python/larch/review/review_types.py

Add the frozen canonical block type; canonical heading/ID parsing; a shared line-level canonical-heading operation; fence-aware segmentation; explicit `finding-heading`, `oos-heading`, `item-heading`, and `level-three-heading` boundary modes; security classification; OOS-eligibility classification; OOS-eligible non-security counting; and public `finding_dedup_key`.

Reimplement compatibility finding parsers through the owner with FINDING-only filtering. Preserve `boundary="finding_heading"` and `boundary="any_heading"` compatibility, mapping the latter to fence-aware `level-three-heading` boundaries. Keep this module leaf-like and free of imports from review, issue, design, state, report, or lint consumers.

### UPDATED: python/larch/review/review_aggregate.py

Replace `_ITEM_BLOCK_RE` and shared heading parsing with `parse_blocks()` and owner heading helpers.

Preserve the existing level-three-heading aggregation contracts explicitly:
- `_finding_blocks`, `_count_finding_blocks`, scope splitting, merge validation, and FINDING-only count paths must use `level-three-heading` boundaries, filter to `kind == "FINDING"`, and must not admit OOS blocks from mixed input.
- Mixed FINDING-plus-OOS `_item_blocks`, prune, renumber, and aggregation paths must also use `level-three-heading` boundaries and retain both kinds.
- Do not replace either existing level-three termination contract with `finding-heading` or `item-heading`.

Keep aggregator-specific malformed-output checks and heading rewrites local where they enforce a distinct validation policy.

### UPDATED: python/larch/review/review_and_fix.py

Replace duplicated canonical FINDING/OOS heading and block classification logic with shared parsing, shared line-heading operations where only a line scan is needed, and security helpers using the former boundary contract for each path.

Preserve skipped-item handling, severity policy, malformed-output diagnostics, and any intentional line-level preamble or severity scans without leaving a duplicate canonical parser regex.

### UPDATED: python/larch/review/batch_report.py

Replace local FINDING heading and OOS-tag classification copies with parsed blocks, shared heading operations, OOS-eligibility policy, and security classification.

Preserve compatibility callers that use `boundary="any_heading"` by keeping their behavior mapped to `level-three-heading` plus explicit FINDING filtering. Preserve coder-log `SKIPPED:` parsing because it is not reviewer-item Markdown grammar.

Remove only helpers whose remaining consumers are migrated in this change.

### UPDATED: python/larch/review/round_runner.py

Replace imports and uses of `_FINDING_RE` and `_OOS_HEADING_RE` from `batch_report.py` with `review_types` operations.

Preserve preamble behavior, OOS filtering, and interior-heading nit-count behavior. Use the shared line-level canonical-heading operation for retained line scans so deleting batch-report regexes does not create an import/runtime failure or trigger the adoption ratchet.

### UPDATED: python/larch/review/compose_review.py

Replace live canonical FINDING/OOS heading parsing and block segmentation with shared parser and heading helpers.

Preserve compose-specific policy for rejected headings, historical identifiers, and synthetic `REJ_*` / `OOS_C_*` IDs, which remain local distinct grammar.

### UPDATED: python/larch/review/voting.py

Remove the copied `is_security_block_text()` implementation and import the owner classifier. Adopt shared heading/ID parsing wherever this module consumes canonical reviewer blocks.

Keep ballot and vote-line parsing separate from reviewer-item grammar.

### UPDATED: python/larch/review/calibration_replay.py

Document and retain calibration ballot heading matchers as a distinct historical-ballot grammar, not canonical reviewer-item parsing.

Ensure its patterns remain outside the canonical grammar migration and are explicitly excluded by the narrow lint detector or protected with a reason-bearing suppression. Do not force historical ballot IDs into canonical numeric FINDING/OOS form.

### UPDATED: python/larch/review/plan_review_tally.py

Use the shared parser, the boundary mode matching current artifact-block behavior, security classifier, and dedup helper for canonical plan-review artifacts. Use `item-heading` only where current behavior truly ends at the next canonical item heading.

Preserve tally-specific ordering, vote results, and FINDING/OOS outcome policy.

Retain the existing local fallback: when canonical parsing yields no blocks but normalized text is nonblank, preserve the single-chunk fallback and any current preamble split used for artifact-pool construction and deduplication.

### UPDATED: python/larch/review/plan_review_common.py

Replace direct canonical FINDING-heading counting with the owner parser while preserving plan-review-specific result handling.

### UPDATED: python/larch/review/plan_review_findings.py

Replace local block segmentation and heading extraction with `parse_blocks()` and owner heading helpers. Preserve finding rendering, plan-review field extraction, and any explicit compatibility alias needed by current callers.

### UPDATED: python/larch/review/plan_review_loop.py

Replace imports of the moved private dedup helper with `review_types.finding_dedup_key` or the explicitly planned compatibility alias. Do not retain a local dedup implementation.

### UPDATED: python/larch/review/plan_review.py

Update dedup-helper imports and any re-export compatibility surface after the helper move. Preserve intentional external import compatibility explicitly and update affected tests to cover the supported import path.

### UPDATED: python/larch/review/plan_review_accepted_audit.py

Replace the wider alphanumeric block regex with canonical shared parsing. Intentionally reject nonnumeric IDs and require exactly `###`, matching the approved canonical grammar.

### UPDATED: python/larch/review/plan_review_gate_b.py

Replace local FINDING block segmentation and ID extraction with shared parsing in the boundary mode matching current behavior. Preserve Gate B filtering and ordering.

### UPDATED: python/larch/review/plan_review_round.py

Replace canonical FINDING/OOS extraction and counting copies with the owner parser and helpers. Keep reviewer-output validation rules that intentionally diagnose malformed text.

### UPDATED: python/larch/review/review_tally.py

Replace canonical heading and block parsing copies with the shared owner. Preserve vote-row and classification-table grammars.

### UPDATED: python/larch/issue/oos.py

Remove its block iterator and security-regex copies. Use shared parsing, OOS-eligibility policy, and `is_security_block_text()`.

Preserve OOS eligibility, vote-tally checks, header normalization, and fail-closed classifier handling.

### UPDATED: python/larch/issue/file_oos.py

Replace `_count_non_security_markdown` and copied security classification with `count_non_security_blocks()` and `is_security_block_text()`.

Reimplement `_parse_oos_blocks` as a thin adapter over `review_types.parse_blocks()` using `oos-heading` boundaries and explicit `kind == "OOS"` filtering, preserving the existing `OosItem` shape and rendered-block behavior. This preserves OOS-only combined-text extraction when intervening FINDING headings occur.

Verify that the shared counter preserves this module’s existing semantics: count canonical OOS blocks and explicitly tagged legacy FINDING blocks only; exclude bare FINDING blocks; then exclude security blocks. Preserve filing, issue-cap rollup, and annotation behavior.

### UPDATED: python/larch/issue/oos_disposition.py

Replace its non-security counter and security classifier with the owner helpers. Preserve disposition state, output contracts, and the same OOS-eligibility semantics as filing.

### UPDATED: python/larch/issue/oos_filer.py

Replace copied `_is_security_block` implementation and private `file_oos.py` segmentation dependencies with `review_types.is_security_block_text()` and the shared/adapter OOS parsing surface.

Preserve current filer decisions and combined multi-block behavior.

### UPDATED: python/larch/issue/rejected_analysis.py

Replace the lenient `#{1,6}` parser with canonical shared parsing. Require exactly `###` while preserving analysis output and field extraction.

### UPDATED: python/larch/issue/_oos.py

Replace repeated canonical block segmentation with `parse_blocks()` in the matching boundary mode. Preserve issue-specific selection and rendering.

### UPDATED: python/larch/issue/_ground_truth.py

Replace `_GT_HEADING_RE` and `_markdown_blocks_by_heading()` canonical segmentation with shared heading parsing and `parse_blocks()` in the boundary mode that preserves current per-ID title/body extraction.

Preserve the dictionary shape, duplicate-ID behavior, output ordering, and local field extraction. Add fenced-heading and mixed FINDING/OOS coverage so this module cannot remain a second grammar owner.

### UPDATED: python/larch/issue/audit_runs.py

Replace canonical reviewer-item segmentation with shared parsing and retain audit-run-specific reporting, filtering, and malformed-input behavior.

### UPDATED: python/larch/design/design_oos.py

Replace copied block segmentation, security classification, and non-security counting with the shared owner APIs.

Use `oos-heading` plus OOS filtering for paths that currently process OOS-only combined text, including post-cap flows; use another documented mode only where the existing path demonstrably has different termination semantics. Preserve promotion, deduplication, filing eligibility, and bare-FINDING exclusion.

### UPDATED: python/larch/core/redact.py

Replace canonical FINDING block segmentation in submodule-path scrubbing with shared FINDING-only parsing. Preserve exact rendered output and submodule scrub behavior.

### UPDATED: python/larch/state/dirty_tree.py

Parse canonical finding headings through the owner when looking for scope-reduction markers. Preserve Concern-field fallback detection and code-fence exclusion.

### UPDATED: python/larch/report/review_phase_detail.py

Replace the FINDING/OOS block regex with shared block parsing. Preserve field extraction, rejected-OOS filtering, title cleanup, and report limits.

### UPDATED: python/larch/report/progress_report.py

Replace `_extract_oos_block` dynamic canonical-heading segmentation with `review_types.parse_blocks()` using the boundary mode matching its existing `(?=^### |\Z)` behavior, likely `level-three-heading`, plus explicit OOS filtering.

Replace copied security classification with `is_security_block_text()`. Preserve report output, block selection, and any preamble behavior.

### UPDATED: skills/fluff-analysis/scripts/fluff-analysis.py

Replace canonical reviewer-item segmentation with the Python owner through the existing supported invocation path, or add a narrow reason-bearing suppression only if the script’s syntax is demonstrably a distinct noncanonical grammar.

Preserve fluff-analysis output contracts.

### UPDATED: python/larch/lint/lint_shared_convention_regex.py

Add the canonical FINDING/OOS grammar detector, owner allowlist, guidance text, and AST coverage for relevant regex-call literals and module-level pattern assignments.

Scope detection to duplicate canonical heading parsing and multiline/block-segmentation forms. Do not flag migrated owner API calls, distinct calibration ballot grammars, vote lines, generated-output templates, field-extraction regexes, or deliberate malformed-input diagnostics. Preserve reason-bearing suppression requirements and deterministic output.

### NEW: python/tests/review/test_review_types.py

Cover:
- canonical FINDING and OOS parsing, IDs, titles, mixed blocks, empty input, preamble-only input, CRLF input, exact heading depth, numeric IDs, and fenced-code examples;
- each explicit boundary mode, including unrelated level-three headings between canonical items and intervening FINDING headings between OOS blocks for `oos-heading`;
- compatibility-wrapper FINDING-only behavior, `boundary="finding_heading"`, `boundary="any_heading"`, and current default behavior;
- security tags, focus-area forms, case handling, inline-code and fenced-code exclusions;
- OOS eligibility for canonical OOS, `[OUT_OF_SCOPE]` FINDING, `[OOS]` FINDING, supported trailing-tag forms, and bare FINDING exclusion;
- `count_non_security_blocks()` parity for mixed files, tagged legacy FINDING blocks, bare FINDING blocks, and security-tagged eligible items;
- dedup-key parity with existing Location, Concern, normalization, and fallback cases.

### UPDATED: python/tests/lint/test_lint_shared_convention_regex.py

Cover direct and compiled canonical block-heading regex detection, module-level assignment detection, owner exemption, retained line-level owner-operation migration, distinct vote-line, calibration-ballot, and field-regex non-matches, reason-bearing suppression, deterministic reporting, and malformed-source handling.

### UPDATED: python/tests/review/test_review_aggregate.py

Add or preserve mixed FINDING/OOS cases proving:
- FINDING-only aggregation, scope splitting, and count paths use level-three-heading ends and exclude OOS blocks;
- mixed-item paths retain level-three-heading behavior;
- intervening `### OOS_1:` and unrelated `### Notes:` sections do not become part of preceding FINDING or item blocks.

### UPDATED: python/tests/review/test_compose_review.py

Cover shared-parser migration while preserving compose-specific rejected and synthetic identifier handling.

### UPDATED: python/tests/review/test_plan_review.py

Update dedup-helper import or compatibility-surface expectations and preserve plan-review behavior after centralization.

### UPDATED: python/tests/review/test_review_and_fix.py

Exercise shared line-heading and parser migration while preserving skipped-item handling, severity behavior, and malformed-output diagnostics.


Cover `any_heading` compatibility through the shared level-three-heading behavior where existing aggregation helpers expose or rely on it.


Exercise `round_runner.py` behavior after removal of batch-report regex imports, including preamble handling, OOS filtering, and interior-heading nit counting.

### UPDATED: python/tests/core/test_redact.py

Cover FINDING-only shared segmentation while preserving submodule scrub output exactly.

### UPDATED: python/tests/issue/test_file_oos.py

Add parity coverage for `_parse_oos_blocks` through the adapter, including multi-block combined text with an intervening FINDING heading, preserved `OosItem` fields, and exact OOS-only boundaries.

### UPDATED: python/tests/issue/test_oos_filer.py

Run and extend focused coverage for shared security classifier and OOS parsing migration, including multi-block combined filing input, if this suite exists under the current test layout.

### UPDATED: python/tests/issue/test_analyze_issues.py

Extend focused `_ground_truth.py` coverage for mixed canonical blocks, fenced canonical-heading examples, and preserved duplicate-ID behavior.

### UPDATED: python/tests/report/test_progress_report.py

Extend affected progress-report coverage for canonical OOS extraction, level-three-heading termination, and security classification if this is the repository’s focused test path; otherwise update the existing focused progress-report suite identified from the test layout.

## Edge cases

- Ignore `### FINDING_1:` and `### OOS_1:` examples inside fenced code blocks.
- Do not accept one, two, four, five, or six hash heading depths as canonical blocks.
- Do not widen canonical IDs beyond uppercase `FINDING_<digits>` and `OOS_<digits>`.
- Preserve titles containing colons, brackets, security labels, and legacy OOS tags.
- Keep boundary semantics explicit:
  - FINDING-only compatibility paths using `any_heading` remain `level-three-heading`;
  - `review_aggregate.py` FINDING-only and mixed-item paths remain `level-three-heading`;
  - OOS-only combined-text paths that historically stop only at another OOS item use `oos-heading`;
  - `item-heading` is reserved for callers whose current contract actually ends at the next canonical item heading.
- A nonblank artifact with no canonical heading must retain `plan_review_tally.py`’s existing local fallback rather than disappearing from tally input.
- `count_non_security_blocks()` must count only OOS-eligible blocks: canonical OOS and explicitly tagged legacy FINDING blocks. Bare FINDING blocks remain excluded, including in mixed input.
- Do not classify security tokens shown only inside code examples as real tags.
- Ensure security-tagged eligible FINDING and OOS blocks receive the same security result.
- Keep malformed-heading detection available to aggregators and validators without making malformed input part of canonical parsing.
- Preserve output text, whitespace, trailing-newline details, `OosItem` shape, and duplicate-ID behavior where consumers render or store parsed blocks.
- Do not flag regexes for vote rows, calibration ballots, classification IDs, generated headings, field labels, or explicit malformed-input diagnostics in the lint.

## Failure modes

- A wrong boundary-mode mapping could absorb unrelated Markdown sections, truncate valid fields, or change caller-specific preamble behavior.
- Mapping legacy `any_heading` to `finding-heading` or `item-heading` would incorrectly fold `### OOS_*:` or `### Notes:` sections into prior FINDING blocks.
- Mapping `_item_blocks` to `item-heading` would change mixed prune/renumber behavior because its live contract ends at any level-three heading.
- Omitting the `oos-heading` mode or leaving `_parse_oos_blocks` live would retain a second grammar owner and alter OOS-only combined-text extraction after an intervening FINDING heading.
- Omitting `kind` filtering in `review_aggregate.py` could admit OOS blocks into FINDING-only aggregation and counts.
- Broadening the shared non-security counter to all FINDING blocks could over-count filing/disposition candidates and file in-scope findings as OOS.
- Removing local regex definitions before migrating `round_runner.py`, `_ground_truth.py`, `progress_report.py`, or other imports could create import-time or runtime failures.
- Moving the dedup helper without updating `plan_review.py` and `plan_review_loop.py` could leave broken imports or an unintended second owner.
- An overbroad lint detector could reject valid calibration ballots, vote/output grammars, or deliberately retained diagnostics; an underbroad detector could leave an unowned canonical parser copy.
- Security-classification drift could publish a security OOS item or incorrectly hold a public item.
- Replacing validation regexes indiscriminately could remove diagnostics for malformed reviewer output.
- Importing from higher-level issue or review modules could create cycles. Keep `review_types.py` leaf-like and free of consumer imports.

## Testing strategy

1. Run owner, aggregate, compose, and lint tests:
   - `python3 -m pytest python/tests/review/test_review_types.py python/tests/review/test_review_aggregate.py python/tests/review/test_compose_review.py python/tests/lint/test_lint_shared_convention_regex.py -q`

2. Run affected review and plan-review tests:
   - `python3 -m pytest python/tests/review/test_review_and_fix.py python/tests/review/test_review_tally.py python/tests/review/test_voting.py python/tests/review/test_plan_review.py python/tests/review/test_plan_review_accepted_audit.py python/tests/review/test_plan_review_round.py -q`

3. Run affected issue, design, core, state, and report tests:
   - `python3 -m pytest python/tests/issue/test_oos.py python/tests/issue/test_file_oos.py python/tests/issue/test_oos_filer.py python/tests/issue/test_analyze_issues.py python/tests/design/test_design_oos.py python/tests/core/test_redact.py python/tests/state/test_dirty_tree.py python/tests/report/test_review_phase_detail.py -q`
   - Run the existing focused progress-report suite, updating the command if its current test path differs from `python/tests/report/test_progress_report.py`.
   - If `python/tests/issue/test_oos_filer.py` is not the repository’s focused filer suite path, run the existing focused `oos_filer` coverage identified from the test layout instead.

4. Run affected audit-run, calibration-replay, and fluff-analysis coverage identified from their current test locations, including canonical-heading, fenced-code, mixed-block, and retained distinct-ballot cases.

5. Run the adoption ratchet directly:
   - `python3 python/cli.py lint shared-convention-regex`

6. Run lint and type checks only for changed Python files through the documented changed-file workflow. Confirm that no canonical FINDING/OOS heading or block-segmentation regex remains outside `review_types.py`, except narrow reason-bearing suppressions for intentionally different validation or historical-ballot grammars.

## Acceptance

1. Run owner, aggregate, compose, and lint tests:
   - `python3 -m pytest python/tests/review/test_review_types.py python/tests/review/test_review_aggregate.py python/tests/review/test_compose_review.py python/tests/lint/test_lint_shared_convention_regex.py -q`

2. Run affected review and plan-review tests:
   - `python3 -m pytest python/tests/review/test_review_and_fix.py python/tests/review/test_review_tally.py python/tests/review/test_voting.py python/tests/review/test_plan_review.py python/tests/review/test_plan_review_accepted_audit.py python/tests/review/test_plan_review_round.py -q`

3. Run affected issue, design, core, state, and report tests:
   - `python3 -m pytest python/tests/issue/test_oos.py python/tests/issue/test_file_oos.py python/tests/issue/test_oos_filer.py python/tests/issue/test_analyze_issues.py python/tests/design/test_design_oos.py python/tests/core/test_redact.py python/tests/state/test_dirty_tree.py python/tests/report/test_review_phase_detail.py -q`
   - Run the existing focused progress-report suite, updating the command if its current test path differs from `python/tests/report/test_progress_report.py`.
   - If `python/tests/issue/test_oos_filer.py` is not the repository’s focused filer suite path, run the existing focused `oos_filer` coverage identified from the test layout instead.

4. Run affected audit-run, calibration-replay, and fluff-analysis coverage identified from their current test locations, including canonical-heading, fenced-code, mixed-block, and retained distinct-ballot cases.

5. Run the adoption ratchet directly:
   - `python3 python/cli.py lint shared-convention-regex`

6. Run lint and type checks only for changed Python files through the documented changed-file workflow. Confirm that no canonical FINDING/OOS heading or block-segmentation regex remains outside `review_types.py`, except narrow reason-bearing suppressions for intentionally different validation or historical-ballot grammars.

diff_added: 455
diff_deleted: 745
mechanical_churn: false
oversize_override: operator
diff_lines: 1200

## Test plan
(no test plan section in plan-file)
