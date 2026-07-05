### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: OOS acceptance threshold and prompt-regression coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: accept_oos could drift from accept_finding or rendering could revert to materiality wording without CI failure, and design 2-judge OOS acceptance is untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add accept_oos/classify_oos_result unit tests, rendering legitimacy assertions, and design/implement paired 2-judge threshold tests.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: main-agent OOS promotion ignores the accepted-only contract
- **Reviewer(s)**: dyn-dyn-oos-routing
- **Severity**: important
- **Concern**: _promote_aggregate_oos_pool now ignores oos-aggregate-pool.md and promotes every non-security block from oos-accepted-main-agent.md without a Result=accepted check or aggregate trigger, diverging from the design contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-oos-routing: Align implement promotion with design: only promote main-agent blocks that carry Result=accepted (or an explicit main-agent acceptance marker), or fold main-agent accepted OOS through the same oos serialize eligibility rules in python/larch/issue/oos.py:86-97 before appending to oos-accepted-review.md. Restore or replace the aggregate trigger if single low-severity main-agent items should not file alone.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

