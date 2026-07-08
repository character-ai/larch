### FINDING_1:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/voting.py:1138-1180
- **Concern**: Alias parsing needs a grammar gate, not just ballot-id-set membership.. Scenario: With a `finding-only` ballot, the new alias path would treat `OOS_1:` as a valid stand-in for `FINDING_1`, so a voter that emits only `OOS_*` lines could evade `JUDGE_ERROR`, stay in the quorum, and make parse-rate retry/removal behave wrong.
- **Proposed resolution**: Only derive aliases when `id_grammar == "finding-oos"`, or pass the grammar into `alias_ballot_id` and return blank for finding-only ballots; add a regression test that `parse-rate-check` on a finding-only ballot still rejects `OOS_*` lines.



### FINDING_2:
- **Reviewer(s)**: Codex-dyn-Vote Parser Collision
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: plan.txt:59-78,91-106
- **Concern**: Plan-review alias recovery is not covered by a regression test. Scenario: The plan updates python/larch/review/plan_review_tally.py alias-sensitive paths, but the added tests only cover python/larch/review/voting.py and python/larch/review/review_tally.py; relabeled OOS_k votes can still drift in _tally_votes_for_id, _votes_and_severities_for_item, _vote_and_severity_for_slot, or _write_findings_classification without detection
- **Proposed resolution**: Add a focused python/tests/review/test_plan_review.py case that feeds a FINDING_1-only ballot plus OOS_1 votes and a collision ballot, then assert count, severity, and classification TSV stay aligned



