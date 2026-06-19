### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review_round.py:536-542
- **Concern**: Plan record gates contradict execute_round control flow for degraded-empty-collector. Scenario: Record-when requires ledger rows whenever findings-classification.tsv exists and excludes degraded-empty-collector only when that file is missing, but execute_round returns early at the degraded-empty-collector branch before the success-tail hook; a literal Record-when implementation would write zero-count rows for collector-failure rounds and can prune the full panel in round 3 after two infrastructure failures rather than reviewer precision history
- **Proposed resolution**: Add degraded-empty-collector to the unconditional do-not-record list (even when classification exists), align Edge cases with that rule, and add a test_plan_review_round negative case that a degraded-empty-collector round does not append ledger rows



### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:2054-2058
- **Concern**: Code-review still records prune ledger on main-agent-vote-required while plan-review excludes MAV recording. Scenario: MAV tally writes preliminary findings-classification.tsv with voting_result=rejected for every item when effective judges are 0. review_core calls _record_prune_round before returning main-agent-vote-required. Precision pruning now aggregates rejected_count, so stale MAV rows can make net score ≤ 0 even when a later MainAgent re-tally would accept findings. Step 5 exits on MAV without re-recording the ledger for that round.
- **Proposed resolution**: Skip _record_prune_round when tally TALLY_STATUS is main-agent-vote-required (match execute_round in python/plan_review_round.py). Re-record only after a settled post-MAV tally for the same round, or clear that round from the ledger until MAV completes.



### FINDING_3:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:341-358; python/plan_review_round.py:56-66
- **Concern**: Plan-mode pruning preserves whitespace token splitting even though planned label-map labels can contain spaces. Scenario: A dynamic slot such as dyn-cursor-plan-api-contract maps to Cursor-dyn-Api Contract; findings-classification.tsv writes that full finding_reviewers value, but whitespace splitting turns it into Cursor-dyn-Api and Contract, so accepted/rejected/total stay 0 and the productive combo can be pruned in round 3
- **Proposed resolution**: Split plan-mode reviewer cells on commas only and trim full tokens, or compare against full label-map values; make the planned plan-mode fixture use a space-containing dynamic slot label



