### FINDING_27: Manual synthetic-stall acceptance test is missing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Acceptance criterion #10 requires a demonstrated manual synthetic-stall integration run covering Step 18a dry-run consumer behavior and dev-clone issue filing, but the branch only shows script-level and offline harness coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: Retry policy table lacks full doc/code parity
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The markdown retry-cap table can drift from `retry_cap_for` / `retry_delay_for`; current harness coverage only samples some classes, so documented retry limits may disagree with runtime behavior while CI still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.



