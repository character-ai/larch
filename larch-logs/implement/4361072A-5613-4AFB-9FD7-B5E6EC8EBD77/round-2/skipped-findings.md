### FINDING_3: Parse-rate gate rejects vote-only or partial-axis outputs that tally can still parse
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `is_substantive_vote_for_id` requires a vote plus all four rating axes, while tally/parser behavior still accepts or records vote-only and partial-axis lines. Legacy or partially compliant judges may be retried, marked failed, or dropped instead of producing degraded but useful forensic rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.



