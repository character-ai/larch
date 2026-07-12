# Review Round 1

- Mode: `diff`
- 8 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Redact reconstruction duplicates or resurrects embedded OOS sections
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-boundary-modes
- **Severity**: major
- **Concern**: `scrub_submodule_paths` reconstructs output from overlapping `FINDING` and `OOS` parsed blocks under `finding-heading` boundaries. Intervening OOS sections can be duplicated when a finding is retained or resurrected when an adjacent finding is scrubbed, changing the prior scrub boundaries and potentially preserving sensitive submodule paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-boundary-modes: - **correctness** `python/larch/core/redact.py:546-580` — `scrub_submodule_paths` now calls `parse_blocks(..., boundary="finding-heading")` and then rebuilds output from every kept `ParsedBlock`, always retaining non-`FINDING` blocks (`kind != "FINDING"` → `keep.add(...)`). With `finding-heading`, a `### FINDING_*` block runs until the next `### FINDING_*`, so it absorbs intervening `### OOS_*` text, while each `### OOS_*` heading still starts its own block. On mixed input such as `### FINDING_1` → `### OOS_2` → `### FINDING_3`, the function can emit both the bloated `FINDING_1` block and a separate `OOS_2` block, duplicating the OOS section and changing scrub boundaries versus the old `re.split(r"(?=^### FINDING_)", ...)` path, which never re-emitted standalone OOS slices. **Suggested fix:** drive scrubbing from FINDING-only slices (`parse_findings_text(..., boundary="finding_heading")` or `parse_blocks` + `kind == "FINDING"`), preserve only preamble plus those FINDING blocks, and do not separately keep non-`FINDING` canonical blocks; add a mixed FINDING/OOS regression test in `python/tests/core/test_redact.py`.


### FINDING_2: Security header recognition rejects whitespace after `###`
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Security-header recognition no longer accepts whitespace after `###`, so headings such as `### OOS_1: [security] private` may not be classified as security and could enter public OOS filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_3: OOS block recovery uses a divergent local segmentation regex
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: `design_oos._block_range` uses a local OOS segmentation regex instead of shared `parse_blocks`/`oos-heading` semantics. Sentinel map recovery may miss blocks recognized by the shared parser or fail when FINDING headings intervene.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_5: In-scope filtering can leak embedded OOS text into findings
- **Reviewer(s)**: dyn-dyn-boundary-modes
- **Severity**: major
- **Concern**: `_filter_in_scope` uses `finding-heading`, which absorbs intervening canonical OOS sections into preceding FINDING blocks. Although standalone OOS blocks are excluded, their bodies can remain embedded in retained findings and leak into `findings-in-scope.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-boundary-modes: - **correctness** `python/larch/review/round_runner.py:144-149` — `_filter_in_scope` also uses `finding-heading`, then writes only `kind == "FINDING"` blocks that fail `is_oos_eligible_block`. That mode intentionally keeps interior `### Details` headings inside a finding, but it also absorbs intervening canonical `### OOS_*` sections into the preceding finding block. A standalone OOS block is dropped from `kept`, yet its body can remain inside the kept finding block, so OOS text can leak back into `findings-in-scope.md` when accepted artifacts interleave FINDING and OOS headings. `python/tests/review/test_review_types.py:44-47` documents the absorption; this path amplifies it now that filtering uses `is_oos_eligible_block` instead of the old broken first-line `_OOS_HEADING_RE` check. **Suggested fix:** after selecting kept FINDING blocks, strip embedded canonical OOS sections from each block body (or segment with `item-heading`, drop `kind == "OOS"` slices, and rejoin FINDING bodies) while still not terminating at interior non-canonical `### Details` lines; add a mixed FINDING/OOS `_filter_in_scope` test.


### FINDING_6: Missing OOS adapter parity tests for intervening FINDING headings
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The OOS adapter lacks regression coverage for combined OOS/FINDING/OOS input, so boundary handling may silently merge or drop content across an intervening FINDING heading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_7: Missing mixed-boundary review aggregate tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Required mixed FINDING/OOS level-three-heading tests are absent for `_finding_blocks`, `_item_blocks`, and `_count_finding_blocks`, leaving boundary regressions that could admit OOS content into FINDING-only counts or absorb `### Notes` sections undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_8: Missing ground-truth tests for fenced and mixed canonical headings
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: No new `analyze-issues` tests cover fenced heading-like text or mixed FINDING/OOS canonical blocks after migration to shared parsing, leaving fence-state and mixed-block regressions untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_9: Canonical FINDING parsing remains local in compose_review
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: `compose_review` still owns local canonical FINDING heading regex parsing, allowing Gate C and compose paths to diverge from `review_types` semantics. Synthetic REJ/OOS_C grammar may remain local, but canonical parsing needs migration or an explicit suppression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
