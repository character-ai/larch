### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/findings_ledger.py:29-62
- **Concern**: [SCOPE-REDUCTION] Ledger row assembly is left to review_tally and plan_review_tally without a shared field extractor. Scenario: Callers can populate title/file_line/reason differently across code-review vs plan-review ballot shapes (Concern vs what, heading title vs empty FINDING_N line), so reviewers see inconsistent keys and prompt dedup misses near-duplicates the feature targets
- **Proposed resolution**: python/findings_ledger.py should own one entry_from_ballot_block helper (reuse plan_review._finding_dedup_key Location/Concern parsing and review_aggregate._problem_text for code-review blocks); both tally sites call it with outcome and YES/total only

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/findings_ledger.py:31-34
- **Concern**: [SCOPE-REDUCTION] ledger_root mirrors review_tally._nested_implement_round instead of sharing it. Scenario: A duplicated nested-round predicate can drift from review_tally.py:105-125; writer and renderers then disagree on IMPLEMENT_TMPDIR/round-N roots and round 2+ prompts read an empty or wrong ledger
- **Proposed resolution**: Import or move _nested_implement_round to a shared module and call it from ledger_root; do not reimplement the parent-resolution rules

### FINDING_10:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:3915-3941; python/rendering.py:847-877
- **Concern**: [SCOPE-REDUCTION] Mutable inline ledger rows make Codex prompt sentinel replay non-deterministic. Scenario: A specialist prompt sidecar stores a hash of the originally rendered prompt. The plan re-renders sentinel prompts from a mutable findings-ledger.tsv path, and default-derives a ledger when the sentinel omits FINDINGS_LEDGER_FILE. If the ledger gains rows after the original render, the reconstructed prompt changes and the hash check can reject a valid retry or replay.
- **Proposed resolution**: Keep the prompt stable by injecting only the ledger path plus duplicate-policy rules. Do not inline ledger rows in render specialist. During sentinel replay, use FINDINGS_LEDGER_FILE only when the sentinel stored it, and do not default-derive a ledger for older sentinels.
