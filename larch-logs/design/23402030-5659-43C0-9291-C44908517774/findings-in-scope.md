### FINDING_1: Preserve per-item serialization and abort ordering
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Batching adjudication before serialization can change existing partial-output and security-abort behavior. Code review must preserve per-item classification, ledger, and score writes while deferring public OOS publication until security checks complete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Keep code-review publish interleaved per item: after each ItemAdjudicationResult is ready, serialize that item before preparing or publishing the next one, and on proposer or security failure stop only after prior items are flushed. State explicitly that run_items may return a full list only when every item succeeds, and that fail-closed abort must not defer all writes until the batch completes.
  - From Cursor-Innovation: State explicitly that code review preserves current per-item order: classification, ledger, and score projection may be written before the security hook; the security gate applies before OOS artifact and public-pool publication only. Narrow the no-partial-serialization rule to artifact routing, or document the preserved partial-row abort contract.
  - From Cursor-Pragmatic: Add an explicit adapter contract: walk ballot order, emit classification/ledger/tally-env/score/artifact side effects per item from cached adjudication only, and halt at the same boundaries as today (proposer failure before row N; security failure after row N classification/ledger, before artifacts). Add a multi-item abort regression in test_review_tally.py if byte parity on failure paths is required.
  - From Cursor-Pragmatic: Clarify that per-item cached adjudication may serialize classification and ledger before artifact routing; security/proposer hooks must complete for an item before its public OOS pool writes; code-review may still write classification/ledger for the failing item before abort. Drop or narrow the blanket no-partial-serialization rule to not-yet-adjudicated items only.
  - From Cursor-Requirements: Add an explicit code-review adapter contract: per item, persist classification/ledger/score from the cached adjudication result, run the block-path security hook, then publish OOS artifacts; on security RuntimeError, keep the existing exit-2 diagnostic after those three writes and before any public OOS output. Clarify that failure-mode partial-serialization applies only to incomplete engine result objects, not this file-write order.
  - From Cursor-Innovation: State explicitly that code review preserves current per-item order: classification, ledger, and score projection may be written before the security hook; the security gate applies before OOS artifact and public-pool publication only. Narrow the no-partial-serialization rule to artifact routing, or document the preserved partial-row abort contract.

### FINDING_2: Converge all ballot-heading consumers on one parser
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: Updating only `split_ballot()` leaves proposer-map, attribution, and neutralization helpers on the old heading grammar, allowing split output and subsequent validation to disagree or weaken fail-closed attribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add _ballot_blocks (and any proposer-map ballot-id enumeration it feeds) to the voting.py update: build the same item-id set and block text from parse_blocks(..., boundary="item-heading") with the same duplicate-heading failure mapping split_ballot preserves, or delegate both split_ballot and _ballot_blocks to one shared helper.
  - From Codex-Innovation: Refactor all ballot-heading consumers on this path to use review_types.parse_blocks, or constrain split_ballot to the same grammar 1. [security] The planned parser migration is incomplete. `split_ballot()` will recognize canonical fenced and whitespace-variant headings, while attribution, neutralization, and proposer-map helpers still use `BALLOT_HEADING_RE`. This can break sidecar validation or accept an anonymous proposer without fail-closed enforcement. Update those consumers or preserve one grammar.
  - From Cursor-Requirements: Extend the voting.py update to route _ballot_blocks and all proposer-map ballot-id enumeration through the same parse_blocks(..., boundary="item-heading") helper used by split_ballot, preserving duplicate-heading SystemExit diagnostics and exact block slices. Add parity tests for tab/whitespace headings across split_ballot and proposer-map validation.

### FINDING_3: Remove duplicated score-policy recomputation
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: Score projection helpers remain a second policy path after the shared engine, potentially recomputing neutral rescue and accepted severity weighting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the refactor scope to _record_plan_review_score_rows and _record_code_review_score_rows: consume cached score_kind, score_result, accepted_weight, neutral_rescued, and unique-finder eligibility from ItemAdjudicationResult only, and add parity tests that fail if those helpers call voting policy functions directly.

### FINDING_4: Preserve duplicate-heading hard failures
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: `parse_blocks()` can return duplicate item IDs without failing, so direct delegation from `split_ballot()` could overwrite block files instead of preserving the existing diagnostic and exit behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: After parsing, detect duplicate `item_id` values before writing block files; on duplicate, print the existing stderr diagnostic and raise `SystemExit(1)`. Add parity tests in `test_voting.py`.
  - From Cursor-Pragmatic: In the split_ballot rewrite, after parse_blocks enumerate blocks, fail with the existing duplicate stderr text and SystemExit(1) when item_id repeats; keep parity cases in test_voting.py.

### FINDING_5: Make non-fileable OOS neutralization engine-owned
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Accepted non-fileable OOS findings must produce a neutral score result in the shared engine; otherwise adapters may diverge or reimplement the policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add one engine-owned rule: for accepted non-fileable OOS items, emit `score_result="neutral"` (not raw `accepted`). Assert it in `test_tally_engine.py` and adapter parity tests.

### FINDING_6: Preserve the zero-voter plan-review stub path
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The `eligible == 0` plan-review path must remain classification-only and must not emit ledger, rendering, or artifact outputs through unified serializers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Keep the `eligible == 0` early return explicit: engine stub contexts produce classification inputs only; skip `_render`, `_write_findings_ledger`, and all artifact writers. Add parity coverage in `test_plan_review.py` proving no `oos.md` / `accepted-plan-findings.md` bytes are written on this path.

### FINDING_7: Define ballot grammar compatibility explicitly
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: `BALLOT_HEADING_RE` and `parse_blocks()` recognize different fenced and whitespace variants, so parser delegation can silently add or drop tally items despite the stated compatibility goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Specify exact outcomes for both cases. Either declare them intentional convergence changes or add a canonical-parser compatibility mode that preserves the old contract

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/tests/review/test_review_tally.py:230-2950; python/tests/review/test_plan_review.py:1846-4261
- **Concern**: [SCOPE-REDUCTION] The plan modifies acceptance suites that must pass unchanged. Scenario: These suites already cover the listed tally paths. Editing them violates the explicit acceptance contract and needlessly enlarges the diff
- **Proposed resolution**: Remove their UPDATED headings. Run them unchanged and keep new coverage in the focused engine and parser tests
