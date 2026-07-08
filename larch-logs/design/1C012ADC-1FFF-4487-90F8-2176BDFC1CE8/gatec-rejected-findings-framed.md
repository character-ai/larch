---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: Alias parsing needs a grammar gate
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The new alias path can misclassify `OOS_*` lines as valid stand-ins for `FINDING_*` on finding-only ballots, which can suppress `JUDGE_ERROR` for out-of-scope relabeling and distort quorum / retry behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Only derive aliases when `id_grammar == "finding-oos"`, or pass the grammar into `alias_ballot_id` and return blank for finding-only ballots; add a regression test that `parse-rate-check` on a finding-only ballot still rejects `OOS_*` lines.


### [Plan Review] FINDING_2

### FINDING_2: Plan-review alias recovery needs dedicated regression coverage
- **Reviewer(s)**: Codex-dyn-Vote Parser Collision
- **Severity**: major
- **Concern**: The plan-review tally path appears to inherit alias-sensitive vote handling without a focused regression test, so relabeled `OOS_k` votes could still drift across count, severity, and classification outputs in `plan_review_tally.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Vote Parser Collision: Add a focused python/tests/review/test_plan_review.py case that feeds a FINDING_1-only ballot plus OOS_1 votes and a collision ballot, then assert count, severity, and classification TSV stay aligned


---LARCH-REJECTED-END---
