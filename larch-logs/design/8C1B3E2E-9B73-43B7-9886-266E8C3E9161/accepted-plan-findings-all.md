### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:47-57
- **Concern**: The testing strategy never runs `python3 python/cli.py token measure-panel-cost`, so it does not verify the acceptance criterion that the aggregator rows for both `design.plan_findings_aggregator` and `review.findings_aggregator` actually drop in scaffold bytes or avoid a ratchet raise.. Scenario: The unit suite can go green while the prompt edit ships without any proof that the measured scaffold-byte reduction happened in both skills, leaving the core acceptance criterion unverifiable.
- **Proposed resolution**: Add a post-change `python3 python/cli.py token measure-panel-cost` check and compare the two aggregator slot-kind rows against the current baseline or committed output to confirm the scaffold-byte drop and no ratchet increase.

