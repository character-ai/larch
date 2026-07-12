### FINDING_1: Plan-review retains parallel policy passes
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Tally Contract Parity
- **Severity**: major
- **Concern**: Plan-review may adjudicate items in `_render`, classification, and ledger paths independently, allowing neutral rescue, scope, outcomes, scores, and artifacts to diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mandate one engine invocation per ballot that returns ordered per-item `ItemAdjudication` results; fan those results into artifact rendering, classification TSV, and ledger writes. Remove standalone policy loops from `_write_findings_classification` and `_write_findings_ledger`.
  - From Cursor-Innovation: Add to the `plan_review_tally.py` section: `_write_findings_classification` / `_write_findings_outputs` must write rows from engine-produced classification cells only; remove the independent per-item `_tally_votes_for_id` re-tally loop. Mirror the `review_tally.py` consume contract.
  - From Codex-Innovation: Pass one engine result through `_render`, classification, and ledger output; remove subsequent per-item vote and policy evaluation
  - From Cursor-Pragmatic: Require one engine pass per item that returns classification row cells, ledger fields, score inputs, and artifact buckets. Make `_render`, `_write_findings_classification`, `_write_findings_ledger`, and the zero-voter stub writers consume that cached result only; delete per-loop recomputation.
  - From Cursor-Requirements: Require one shared engine adjudication per item that feeds all three writers; explicitly name `_write_findings_classification` and `_write_findings_ledger` as consumers (not only `_render`)
  - From Cursor-dyn-Tally Contract Parity: One `tally_engine.run_items()` per ballot; cache `list[ItemAdjudicationResult]`; make classification and ledger thin serializers over that cache; drop per-item policy calls from `_write_findings_classification` / `_write_findings_ledger`.


### FINDING_2: Security classification inputs must remain family-specific
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-Tally Contract Parity, Codex-dyn-Tally Contract Parity
- **Severity**: major
- **Concern**: Code-review and plan-review intentionally use different security inputs and failure behavior; collapsing them into one shared path may reroute security findings or alter fail-closed behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit family hook for security classification input and failure mapping (restored text vs block path; `RuntimeError` vs `SystemExit` translation). Keep artifact restoration separate from the security probe contract.
  - From Cursor-Innovation: Code-review calls `is_security_block` on the neutralized block file; plan-review calls `is_security_block_text` on restored artifact text (`test_plan_review_tally_classifies_security_from_restored_attribution`). Unifying on one path in the engine changes which items reach the public OOS pool vs the private sidecar. List this under preserved intentional differences. Have families supply the `security` boolean (or classifier callable) to the engine; do not hard-code restored text for both paths.
  - From Cursor-dyn-Tally Contract Parity: Keep a family `classify_security(item)` hook; do not fold security detection into shared item prep that always uses restored text or always uses the raw block path.
  - From Codex-dyn-Tally Contract Parity: Compute security status from the restored artifact text in the shared result for both families, before committing classification or public artifacts, and add the code-review neutralized-security regression.


### FINDING_3: Define the engine score-output contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-dyn-Tally Contract Parity
- **Severity**: major
- **Concern**: The planned canonical score-row representation is undefined across families, whose tuple shapes, bonus handling, and scoreboard projections differ.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Have the engine accumulate only per-item adjudication primitives (`fileable_oos`, `neutral_rescued`, `score_kind`, `score_result`, ledger outcome, artifact routing). Keep all TSV string rendering and score-row tuple shapes in family adapters via hooks.
  - From Cursor-Pragmatic: Define an engine-level score contribution struct (per reviewer slot: kind, result, accepted_weight, bonus_eligible). Add family hooks that project it into the existing code-review and plan-review scoreboard accumulators without changing output math.
  - From Codex-dyn-Tally Contract Parity: Declare voting.py the owner of primitive policy predicates and make the engine the sole evaluator that calls them once; adapters must consume immutable engine results and must not recompute policy.


### FINDING_4: Specify family-owned OOS and classification context
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-Tally Contract Parity, Codex-dyn-Tally Contract Parity
- **Severity**: major
- **Concern**: OOS eligibility and classification inputs differ by family, including code-review scope drift and heading tags, `classify_oos_result`, and plan-review prefix handling. An underspecified shared loop can misclassify or misroute findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document scope drift as a code-review adapter pre-step that sets `effective_is_oos` / kind inputs before calling the shared engine. Keep it out of plan-review and out of shared policy.
  - From Cursor-Innovation: Define a narrow family hook (e.g. `resolve_item_context`) that returns `is_oos`, vote-result classifier choice, and security-check text before adjudication. Keep scope drift and heading-tag detection in the code-review adapter only.
  - From Cursor-Innovation: Add to preserved intentional differences: code-review heading-tag OOS promotion stays in the code-review adapter; plan-review remains prefix-only.
  - From Cursor-Pragmatic: Document and implement adapter inputs: is_oos, voting_result, eligible, vote cells, restored artifact text, and security status. Keep scope_drift detection and classify_oos_result in the code-review adapter; pass finalized values into adjudicate_item.
  - From Cursor-dyn-Tally Contract Parity: Add an explicit `prepare_item_context` family hook returning `kind`, post-OOS `result`, and classification `is_oos` before shared adjudication; document scope-drift and heading-tag detection as code-review-only inputs.
  - From Codex-dyn-Tally Contract Parity: Pass an explicit oos_eligible value from the canonical parsed block into the engine, including heading tags and code-review scope drift; do not infer scope from the ID alone.


### FINDING_6: Route ballot parsing through the canonical parser
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-dyn-Tally Contract Parity
- **Severity**: major
- **Concern**: `voting.split_ballot` remains a separate parser, so fenced, malformed, whitespace-variant, or duplicate headings can diverge from `review_types.parse_blocks`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Explicitly route both adapters or the engine through parse_blocks with item-heading boundaries, detect duplicate IDs, and preserve each family's existing fail-closed diagnostics and stub outputs
  - From Codex-Innovation: Explicitly route both adapters through review_types.parse_blocks, preserving duplicate and malformed-input contracts, and add parser-edge parity coverage
  - From Codex-Pragmatic: Add `voting.py` to the firm changes and delegate `split_ballot` to `parse_blocks(..., boundary="item-heading")`, preserving duplicate detection and exact block text; add focused fence and duplicate coverage
  - From Codex-dyn-Tally Contract Parity: Make both adapters use review_types.parse_blocks, or update voting.split_ballot to delegate to it while preserving its CLI errors and output contract; include the parser owner in the firm file set.


### FINDING_7: Preserve the main-agent classification override
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Tally Contract Parity
- **Severity**: minor
- **Concern**: Plan-review classification must continue forcing `rejected` for `main_agent_voter`, while artifact routing and scoring retain their existing behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Document the override in the plan-review adapter contract: classification `result` column stays `rejected` whenever `main_agent_voter` is set, independent of artifact routing.
  - From Cursor-Requirements: Document and implement a family hook (or explicit post-engine override) that preserves the TSV-only `voting_result` override for classification rows only
  - From Cursor-dyn-Tally Contract Parity: Pass `main_agent_voter` into the family adapter; apply the TSV-only `voting_result` override in the classification renderer; delete rescue/score recomputation from `_record_plan_review_score_rows` and consume engine fields instead.


### FINDING_10:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/review/tally_engine.py (planned)
- **Concern**: [SCOPE-REDUCTION] Avoid unified canonical score rows in the shared engine. Scenario: Acceptance requires byte-identical scoreboards, but families use different score-row shapes today (code-review 4-tuples plus `bonus_by_reviewer`; plan-review 5-tuples with inline bonus; code-review adds a Status column). A shared canonical score-row accumulator invites scoreboard convergence outside this piece's scope.
- **Proposed resolution**: Limit engine outputs to adjudication scalars and eligibility flags; let each family adapter build its existing score rows and scoreboard tables unchanged.


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


