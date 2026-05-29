### FINDING_15: Split plan-size-trigger and plan-validator-defects matrix rows
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A single branch matrix row covers `plan-size-trigger|plan-validator-defects` with alternative skip breadcrumbs. The orchestrator could print the wrong Step 3.6 skip breadcrumb while still short-circuiting, breaking status-specific observability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.



### FINDING_16: Check write-cursor failures in advance_step3_cursor
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `advance_step3_cursor` ignores `write-cursor` failure and still returns an incremented cursor, so Entry 2 may assert against the wrong round or fail opaquely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.



### FINDING_6: Pin Gate C panel-failed bypass prose
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The committed branch lacks structural pins for Gate C `panel-failed` bypass prose in `approval-gates.md`. A future edit could drop `panel-failed` from the bypass list while short-circuit breadcrumbs remain, causing agents to route `panel-failed` through Gate B or Step 3.6 incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.



