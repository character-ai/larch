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


### FINDING_5: Make non-fileable OOS neutralization engine-owned
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Accepted non-fileable OOS findings must produce a neutral score result in the shared engine; otherwise adapters may diverge or reimplement the policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add one engine-owned rule: for accepted non-fileable OOS items, emit `score_result="neutral"` (not raw `accepted`). Assert it in `test_tally_engine.py` and adapter parity tests.


