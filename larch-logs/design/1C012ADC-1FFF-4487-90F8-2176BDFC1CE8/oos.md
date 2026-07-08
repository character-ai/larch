### OOS_1: [OUT_OF_SCOPE] `_parse_slot_v2_vote` still calls `parse_judge_vote` with only `finding_id`, so relabeled `OOS_k:` votes stay unreadable in replay flows.
- **Description**: [OUT_OF_SCOPE] `_parse_slot_v2_vote` still calls `parse_judge_vote` with only `finding_id`, so relabeled `OOS_k:` votes stay unreadable in replay flows.. Scenario: Replaying an affected run still reports JUDGE_ERROR for the same ballots, so the alias fix does not carry through calibration replay and those runs remain hard to verify.
- **Reviewer**: Codex-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/calibration/calibration_replay.py:447-448
- **Phase**: design




Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_2: [OUT_OF_SCOPE] Add a plan-review regression for the new alias path
- **Description**: [OUT_OF_SCOPE] Add a plan-review regression for the new alias path. Scenario: `plan_review_tally.py` gains new `_alias_id` wiring, but the plan only adds `voting.py` and code-review tests, so a broken plan-review path could still ship unnoticed.
- **Reviewer**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/review/test_plan_review.py
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### OOS_3: [OUT_OF_SCOPE] Optional ballot hygiene reopens ballot heading generation
- **Description**: [OUT_OF_SCOPE] Optional ballot hygiene reopens ballot heading generation. Scenario: The approach suggests rewriting mixed FINDING_N headers to OOS_N, but the firm plan also says not to change ballot heading generation and the alias fix does not need this extra contract
- **Reviewer**: Codex-dyn-Vote Parser Collision
- **Severity**: minor
- **Focus area**: architecture
- **Location**: plan.txt:2-3,30-35
- **Phase**: design

Vote tally: YES=1 NO=1 JUDGE_ERROR=1 Result=neutral Fileable=false

