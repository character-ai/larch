### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/reviewer-prune.sh:59-297
- **Concern**: [SCOPE-REDUCTION] Plan treats reviewer-prune as a full bash port but the helper is already a thin bash argv wrapper around an inline Python heredoc. Scenario: Re-implementing from bash prose risks subtle ledger/filter drift versus today's behavior and adds unnecessary churn
- **Proposed resolution**: Lift the existing heredoc body into `review_pipeline.reviewer_prune` (plus `lib-prune-decision.sh` helpers); keep the new `review reviewer-prune` CLI as a thin argv relay
