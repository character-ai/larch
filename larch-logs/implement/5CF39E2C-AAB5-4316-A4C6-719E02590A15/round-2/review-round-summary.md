# Review Round 2

- Mode: `diff`
- 7 accepted, 8 rejected (2 exonerated)

## Accepted Findings

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


### FINDING_17: Guard main-agent-vote-required and zero-findings-degraded-panel against bypass lists
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: There is no structural guard ensuring `main-agent-vote-required` and `zero-findings-degraded-panel` stay off bypass or skip lists, so a future edit could add them to bypass prose without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: Restore case-local LARCH_* overrides after two-entry harness
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The two-entry `test-assess-plan-round.sh` case leaves `LARCH_DISPATCH_PLAN_ASSESSORS_SH` and `LARCH_BREADCRUMB_MONITOR_SH` exported to paths under a removed `case_tmp`, so later appended cases or failures could inherit deleted or round-specific mocks and fail or pass for unrelated reasons.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: Commit structural pins for MainAgent re-tally refresh
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The committed branch lacks structural pins for `main-agent-vote-required` re-tally refresh, including `.step3-plan-review-result.env`, `findings-classification.tsv` or `findings-classification-out`, and Step 3 env refresh behavior. Future edits could remove the MainAgent refresh prose while CI stays green, allowing Gate B to consume stale zero-judge state after adjudication.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_6: Pin Gate C panel-failed bypass prose
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The committed branch lacks structural pins for Gate C `panel-failed` bypass prose in `approval-gates.md`. A future edit could drop `panel-failed` from the bypass list while short-circuit breadcrumbs remain, causing agents to route `panel-failed` through Gate B or Step 3.6 incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_8: Pin SKILL runtime cap breadcrumb
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The runtime cap breadcrumb in `skills/design/SKILL.md` is not structurally pinned; only the `approval-gates.md` template is. A future `printf` could revert to returning directly to Gate C while approval-gates tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


