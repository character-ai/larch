### FINDING_1: Align /design Step 3.6 routing prose with assessor integration plan
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `057659aa` asks to align `/design` Step 3.6 routing prose with the assessor integration plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Apply relevant-checks fixes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `e29eab6e` asks to apply relevant-checks fixes from Step 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Address round-one code review feedback
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `5a7cd71d` asks to address round-one code review feedback across `skills/design/SKILL.md`, `skills/design/references/approval-gates.md`, `scripts/test-design-structure.sh`, `skills/design/scripts/test-assess-plan-round.sh`, and `skills/design/scripts/test-assess-plan-round.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_7: Two-entry harness does not behaviorally cover second loop and passive-summary Continue
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The two-entry harness does not exercise the second plan-review-loop or Gate B passive-summary Continue behaviorally, so an orchestrator could skip Step 3.6 after passive-summary Continue while offline harness and prose pins still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Pin SKILL runtime cap breadcrumb
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The runtime cap breadcrumb in `skills/design/SKILL.md` is not structurally pinned; only the `approval-gates.md` template is. A future `printf` could revert to returning directly to Gate C while approval-gates tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Remove redundant short Step 3.5 bypass pin
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: A short Step 3.5 bypass pin duplicates the fuller Gate B bypass list pin, adding maintenance without functional coverage benefit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Large committed run logs inflate review cost
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Large committed `larch-logs/**` files inflate diff size and review time, but this is out of scope for the feature test review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: MainAgent refresh reduces stale zero-judge state
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `main-agent-vote-required` now requires refreshing `.step3-plan-review-result.env` and active-round `findings-classification.tsv` before Gate B, reducing stale zero-judge state consumption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: Passive-summary Continue routes through Step 3.6
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Passive-summary Continue explicitly routes through Step 3.6 before Step 3b.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: Cap-reached no longer skips Gate B
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `cap-reached` no longer implies jumping straight to Gate C while skipping Gate B, avoiding resurfacing stale accepted findings; the new two-entry harness exercises the real `tally-plan-assessor.sh` while stubbing dispatch and monitor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Production assessor dispatch and monitor env overrides remain hardening risk
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/assess-plan-round.sh` still allows `LARCH_DISPATCH_PLAN_ASSESSORS_SH` and `LARCH_BREADCRUMB_MONITOR_SH` overrides in production-like same-UID sessions before returned assessor paths are validated. The reviewer marks this as pre-existing and not introduced or amplified by this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

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

### FINDING_18: [OUT_OF_SCOPE] skipped-empty-findings lacks explicit Step 3.6 disposition
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The `skipped-empty-findings` path says to proceed to Step 3.5 without an explicit Step 3.6 disposition, so operators reading only Step 3 prose may miss that zero-findings still reaches Step 3.6 via Gate B. The reviewer marks this as not introduced by the diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] cap-hit and cap-reached naming remains confusing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `cap-hit` versus `cap-reached` naming remains easy to confuse, creating pre-existing operational ambiguity around which cap path skips Step 3.6. The reviewer marks this as separate cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
