### FINDING_3: Claude/Voter 1 delayed `.done` test proves non-wait behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The Voter 1 delayed `.done` test validates immediate synthetic `.done` backfill instead of proving the dispatcher waits for launcher-owned completion, so it does not catch regressions in Voter 1 barrier inclusion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.



