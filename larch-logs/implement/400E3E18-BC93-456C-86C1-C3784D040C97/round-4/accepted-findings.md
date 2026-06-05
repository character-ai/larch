### FINDING_11: review-summary.json rejected fallback is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The rejected-count fallback from `review-summary.json` is not tested when `review-tally.env` is missing or malformed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_16: Timing report attaches rounds without bounding round end/duration
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-telemetry-ledger-output.txt
- **Severity**: important
- **Concern**: `timing-report.sh` attaches round rows by start time only, so rows ending after the parent step can publish inflated durations that span later steps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-telemetry-ledger-output.txt: Address the concern above.


### FINDING_19: run-logs docs omit new timing-report rounds schema
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `docs/run-logs.md` does not document the additive `rounds` arrays, fields, and attachment rules for committed `timing-report.json`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_2: Implement round timing writers have inconsistent count/idempotency behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Implement in-loop and deferred round timing paths use different writers/count sources and brittle idempotency policies, allowing duplicates, stale bad rows, skipped corrections, or last-writer ambiguity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_20: Design plan loop marks timing emitted without verifying ledger row
- **Reviewer(s)**: dyn-telemetry-ledger-output.txt
- **Severity**: latent
- **Concern**: `_emit_plan_round_timing_row` can set the per-round emitted guard after a best-effort helper exit even if no ledger row landed, preventing later retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-telemetry-ledger-output.txt: Address the concern above.


### FINDING_3: Implement loop timing emit callsites are duplicated and under-tested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_emit_implement_round_timing_row` is copied across many loop branches, while the loop-timing harness does not drive `run_implement_loop`, so missed emissions on continuation/stall paths could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Final summary can freeze stale timing totals
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `render-final-summary.sh` can skip timing regather when `timing-report-final.json` already exists, leaving later Step 6 cleanup marks out of published final timing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: Design MAV deferred timing can be lost on tally-error and lacks coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-handoff-state-output.txt
- **Severity**: important
- **Concern**: Design MAV deferred timing is emitted only after successful re-tally; a tally-error short-circuit can skip `record-plan-review-round-timing.sh`, and tests do not cover this handoff path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-handoff-state-output.txt: Address the concern above.


