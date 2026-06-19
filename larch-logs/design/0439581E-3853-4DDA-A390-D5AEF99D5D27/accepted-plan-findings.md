### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/plan_review_round.py:499-549
- **Concern**: Plan updates plan-review filter fixtures and plan-mode parsing, but omits the native plan-review ledger recording path. Scenario: Normal /design rounds write findings-classification.tsv, but no settled round records reviewer-prune-ledger.tsv; round 3 then has no precision history and fail-opens, so precision-aware pruning never applies to native plan review
- **Proposed resolution**: Add python/plan_review_round.py to the plan: after settled non-pruned tally, record the filtered plan-review-slots.ndjson with the round classification TSV and a slot-to-human label map; keep pruned-empty, tally-error, panel-failed, and MAV no-record paths




### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review_round.py:499-522; python/plan_review_panel.py:226-246
- **Concern**: Native design rounds still never populate reviewer-prune-ledger.tsv. Scenario: Plan-review rounds 1-2 can write findings-classification.tsv, but round 3 filters design/reviewer-prune-ledger.tsv with no live rows, so precision-aware pruning is not applied to /design
- **Proposed resolution**: Add python/plan_review_round.py to the plan and record each non-pruned round after tally writes the classification TSV, using reviewer_prune_record with a slot to _slot_human_label label map so finding_reviewers attribution matches plan-review labels




### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: docs/configuration-and-permissions.md:266-268
- **Concern**: Canonical LARCH_REVIEWER_PRUNE docs stay on the old zero-accepted rule. Scenario: After this PR the env-var documentation will contradict the new net-score and acceptance-rate pruning behavior
- **Proposed resolution**: Add docs/configuration-and-permissions.md to the plan and replace the zero-accepted clause with the precision-aware rule while keeping the off-only override text




### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:1680-1762
- **Concern**: Zero-finding live rounds are not recorded in the prune ledger. Scenario: The plan says zero-finding combos prune by net score, but _zero_findings_branch only records the classification path and never calls _record_prune_round, so two launched rounds with no findings leave no history rows and round 3 cannot prune them
- **Proposed resolution**: Pass prune_ledger into _zero_findings_branch and call _record_prune_round after classification is written; update both zero-finding callers




