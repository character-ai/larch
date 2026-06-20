### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/plan_review_tally.py:236-272,501-575
- **Concern**: Plan-review live agreement is specified as a second vote-assembly path in `_render`, not the same inputs as `_write_findings_classification`. Scenario: `_render` runs before `_write_findings_classification` and the plan only says to reuse `_tally_votes_for_id` plus slot reads. Classification uses `tsv_result`, clears `JUDGE_ERROR` to empty, applies `_sanitize_tsv_cell`, and skips cells when `self.tally_voter_file == voter_file`. A separate assembly path can drift on those rules and fail the planned parity test against emitted TSV even when math in `voting.py` is correct
- **Proposed resolution**: Extract one per-finding helper (e.g. `_classification_agreement_inputs(item_id)`) that returns `(voting_result, voter_votes)` exactly as written to TSV; call it from both `_write_findings_classification` and the voter scoreboard append



