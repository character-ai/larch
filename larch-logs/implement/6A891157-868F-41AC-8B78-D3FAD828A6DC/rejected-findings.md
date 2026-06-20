# Rejected Findings

# Review Round 1

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: Plan-mode attribution does not split pipe-delimited finding_reviewers cells
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Plan-mode prune attribution does not split pipe-delimited `finding_reviewers` cells. A merged accepted plan finding attributed to multiple reviewers is written as `Cursor-Arch|Cursor-Requirements`, so both reviewers record zero accepted findings and can be pruned in round 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Split plan-mode reviewer cells on | as well as comma, preserving full stripped labels.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (0 YES)

### FINDING_12: Plan-review ledger records round_num but pruning filters on prune_round_num
- **Reviewer(s)**: dyn-prune-ledger-output.txt
- **Severity**: important
- **Concern**: Plan-review ledger rows are written with `round_num` (`python/plan_review_round.py:573-574`), but panel pruning uses `prune_round_num` (`plan_review_panel.py:293`, `reviewer_prune_filter` at `--round`). The API allows those values to diverge; when they do, history is keyed to the artifact round while round 3–4 filtering reads the prune round. `_rewrite_prune_ledger` also replaces rows for the recorded round, so a mismatched `round_num` can overwrite prior history instead of appending a new launched round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prune-ledger-output.txt: Record with `prune_round_num` (or `prune_round_num or round_num`) in `_record_plan_review_prune_round` / its `execute_round` call site, matching the filter's round identity.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0


# Review Round 2



