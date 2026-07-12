### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_tally.py:958-987
- **Concern**: Batch run_items plus post-hoc serialization can erase code-review partial outputs on mid-ballot failures. Scenario: Code review appends classification, ledger, score, and artifact rows per item inside the loop; proposer restoration runs before those writes, and security classification runs after classification but before OOS publication. The plan replaces that loop with one context-prep pass and one tally_engine.run_items() call, then thin serializers. If preparation or security work for item N fails before any serializer runs, earlier items that already succeed today will leave no TSV, ledger, tally-env, or artifact bytes on disk.
- **Proposed resolution**: Keep code-review publish interleaved per item: after each ItemAdjudicationResult is ready, serialize that item before preparing or publishing the next one, and on proposer or security failure stop only after prior items are flushed. State explicitly that run_items may return a full list only when every item succeeds, and that fail-closed abort must not defer all writes until the batch completes.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/voting.py:588-605
- **Concern**: _ballot_blocks and proposer-map validation are outside the split_ballot parser convergence. Scenario: FINDING_6 routes voting.split_ballot through review_types.parse_blocks, but _ballot_blocks still keys headings with BALLOT_HEADING_RE for proposer_map_from_ballot, validate_proposer_map_coverage, and validate_proposer_map_for_tally. Tab or whitespace variants that parse_blocks accepts can produce on-disk block files whose stems are absent from _ballot_blocks(ballot_text), yielding proposer-map mismatch or missing-item failures after an otherwise successful split.
- **Proposed resolution**: Add _ballot_blocks (and any proposer-map ballot-id enumeration it feeds) to the voting.py update: build the same item-id set and block text from parse_blocks(..., boundary="item-heading") with the same duplicate-heading failure mapping split_ballot preserves, or delegate both split_ballot and _ballot_blocks to one shared helper.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/review/plan_review_tally.py:70-104
- **Concern**: The plan omits score projection helpers from the no-recompute boundary. Scenario: Plan serializers listed for _render, classification, ledger, and outputs, but _record_plan_review_score_rows still calls neutral_high_severity_rescue_to_oos and accepted_finding_points_from_severities, and review_tally._record_code_review_score_rows still recomputes accepted_weight from vote cells. That leaves a second policy path after run_items and conflicts with the engine owning neutral rescue, fileability, and accepted severity weighting once per item.
- **Proposed resolution**: Extend the refactor scope to _record_plan_review_score_rows and _record_code_review_score_rows: consume cached score_kind, score_result, accepted_weight, neutral_rescued, and unique-finder eligibility from ItemAdjudicationResult only, and add parity tests that fail if those helpers call voting policy functions directly.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/voting.py:912-931
- **Concern**: `split_ballot()` must keep duplicate-heading hard-fail when backed by `parse_blocks()`. Scenario: `parse_blocks(..., boundary="item-heading")` emits one block per heading start and does not reject duplicate `item_id` values. A straight swap would write two `FINDING_1.md` files (last wins) instead of printing `duplicate ballot heading FINDING_1` and exiting 1.
- **Proposed resolution**: After parsing, detect duplicate `item_id` values before writing block files; on duplicate, print the existing stderr diagnostic and raise `SystemExit(1)`. Add parity tests in `test_voting.py`.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: ts
- **Concern**: Failure-mode bullets still conflict on security vs serialization ordering (prior FINDING_5 fix incomplete). Scenario: The plan requires security classification before public OOS publication and also forbids serializing classification, ledger, score, or artifacts from partially built items. Code review today writes classification, ledger, and score rows before `_security_block()` and may abort with those rows already on disk (`review_tally.py` ~958-987). An implementer following the second bullet could reorder outputs and break abort diagnostics or byte parity.
- **Proposed resolution**: State explicitly that code review preserves current per-item order: classification, ledger, and score projection may be written before the security hook; the security gate applies before OOS artifact and public-pool publication only. Narrow the no-partial-serialization rule to artifact routing, or document the preserved partial-row abort contract.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/tally_engine.py
- **Concern**: Engine score-result contract must include non-fileable accepted OOS neutralization. Scenario: Both families set `score_result = "neutral"` when `kind == "oos"`, `result == "accepted"`, and `fileable_oos` is false before score projection (`plan_review_tally.py` ~850, `review_tally.py` ~977). The plan lists score kind/result primitives but does not name this rule. If adapters re-derive it, the duplication returns; if they omit it, scoreboards and unique-finder bonuses drift.
- **Proposed resolution**: Add one engine-owned rule: for accepted non-fileable OOS items, emit `score_result="neutral"` (not raw `accepted`). Assert it in `test_tally_engine.py` and adapter parity tests.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/review/plan_review_tally.py:734-746
- **Concern**: Plan-review `eligible == 0` must stay a classification-only stub path. Scenario: Today `eligible == 0` writes the degraded tally stub, calls `_write_findings_classification()` only, emits `TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required`, and returns without `_render`, ledger write, or OOS/accepted artifact writers. The plan caches `run_items()` for zero-voter stubs but does not pin this early-return branch. A unified post-engine serializer could accidentally run artifact routing or ledger writes on a zero-judge ballot.
- **Proposed resolution**: Keep the `eligible == 0` early return explicit: engine stub contexts produce classification inputs only; skip `_render`, `_write_findings_ledger`, and all artifact writers. Add parity coverage in `test_plan_review.py` proving no `oos.md` / `accepted-plan-findings.md` bytes are written on this path.



### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/review/voting.py:588-618,709-817
- **Concern**: Canonical split parsing leaves attribution and neutralization helpers on the old heading grammar. Scenario: A fenced or whitespace-variant heading is recognized by split_ballot but still misread by _ballot_blocks or neutralization, causing proposer-map failure or fail-open anonymous attribution
- **Proposed resolution**: Refactor all ballot-heading consumers on this path to use review_types.parse_blocks, or constrain split_ballot to the same grammar 1. [security] The planned parser migration is incomplete. `split_ballot()` will recognize canonical fenced and whitespace-variant headings, while attribution, neutralization, and proposer-map helpers still use `BALLOT_HEADING_RE`. This can break sidecar validation or accept an anonymous proposer without fail-closed enforcement. Update those consumers or preserve one grammar.



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_tally.py:869-987
- **Concern**: Specify per-item incremental serialization on code-review abort paths. Scenario: The plan batches context preparation and one run_items() call, then has thin serializers consume cached results. Today the per-item loop appends classification TSV rows (and in-memory ledger entries) for items 1..N-1, then for item N writes classification/ledger before security; on security or proposer failure it returns rc 2 with partial class TSV on disk and no final ledger/tally write. A prep-then-run_items-then-serialize layout can emit zero rows or a different prefix unless ordering is pinned.
- **Proposed resolution**: Add an explicit adapter contract: walk ballot order, emit classification/ledger/tally-env/score/artifact side effects per item from cached adjudication only, and halt at the same boundaries as today (proposer failure before row N; security failure after row N classification/ledger, before artifacts). Add a multi-item abort regression in test_review_tally.py if byte parity on failure paths is required.



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/review/tally_engine.py
- **Concern**: Failure-mode bullets conflict on partial serialization vs preserved code-review ordering. Scenario: Failure modes say not to serialize classification/ledger/score/artifact from a partially built item and to finish security before public OOS publication, while also requiring preserved abort contracts. Code review currently treats vote-complete but pre-security items as serializable for classification and ledger. Literal batch-all-then-serialize reading breaks that contract and reopens the round-1 neutral finding on security-abort ordering.
- **Proposed resolution**: Clarify that per-item cached adjudication may serialize classification and ledger before artifact routing; security/proposer hooks must complete for an item before its public OOS pool writes; code-review may still write classification/ledger for the failing item before abort. Drop or narrow the blanket no-partial-serialization rule to not-yet-adjudicated items only.



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/review/voting.py:912-931
- **Concern**: Require explicit duplicate-ID enforcement when split_ballot delegates to parse_blocks. Scenario: parse_blocks returns every canonical heading, including duplicate item_ids, and does not raise. split_ballot today exits on duplicate headings before write. Delegation without a seen-set check would overwrite block files and lose the duplicate diagnostic contract both tally callers rely on.
- **Proposed resolution**: In the split_ballot rewrite, after parse_blocks enumerate blocks, fail with the existing duplicate stderr text and SystemExit(1) when item_id repeats; keep parity cases in test_voting.py.



### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/tests/review/test_review_tally.py:230-2950; python/tests/review/test_plan_review.py:1846-4261
- **Concern**: [SCOPE-REDUCTION] The plan modifies acceptance suites that must pass unchanged. Scenario: These suites already cover the listed tally paths. Editing them violates the explicit acceptance contract and needlessly enlarges the diff
- **Proposed resolution**: Remove their UPDATED headings. Run them unchanged and keep new coverage in the focused engine and parser tests



### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/voting.py:126,912-931
- **Concern**: The accepted canonical-parser fix leaves ballot compatibility contradictory. Scenario: `BALLOT_HEADING_RE` requires one space and recognizes headings inside fences, while `parse_blocks` accepts tabs or multiple spaces and ignores fenced headings. Direct delegation can silently add or drop tally items despite the plan promising unchanged grammar
- **Proposed resolution**: Specify exact outcomes for both cases. Either declare them intentional convergence changes or add a canonical-parser compatibility mode that preserves the old contract



### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_tally.py:958-987
- **Concern**: The prior security-abort write-order fix is still incomplete for batched run_items.. Scenario: Code review today writes each item's classification, ledger, and score rows before the security probe, then aborts before OOS artifacts; a single batched run_items() call plus the failure-mode ban on partial serialization can skip those rows for the failing item or for all prior items on mid-ballot abort, breaking byte parity and tally-error contracts.
- **Proposed resolution**: Add an explicit code-review adapter contract: per item, persist classification/ledger/score from the cached adjudication result, run the block-path security hook, then publish OOS artifacts; on security RuntimeError, keep the existing exit-2 diagnostic after those three writes and before any public OOS output. Clarify that failure-mode partial-serialization applies only to incomplete engine result objects, not this file-write order.



### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/review/voting.py:588-677
- **Concern**: The prior split_ballot parser-unification fix is still incomplete.. Scenario: Only split_ballot is slated to delegate to review_types.parse_blocks; _ballot_blocks, proposer_map_from_ballot, validate_proposer_map_coverage, and proposer-map mismatch checks still use BALLOT_HEADING_RE, which rejects headings parse_blocks accepts (for example ###\tFINDING_1:). split_ballot can emit block files that proposer validation then treats as missing or extra.
- **Proposed resolution**: Extend the voting.py update to route _ballot_blocks and all proposer-map ballot-id enumeration through the same parse_blocks(..., boundary="item-heading") helper used by split_ballot, preserving duplicate-heading SystemExit diagnostics and exact block slices. Add parity tests for tab/whitespace headings across split_ballot and proposer-map validation.



