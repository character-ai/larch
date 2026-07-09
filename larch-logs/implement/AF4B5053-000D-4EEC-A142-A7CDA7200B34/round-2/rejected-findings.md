### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: Missing dispatch/structure assertions for step-5-resume and step-6-entry hygiene
- **Reviewer(s)**: cursor-specialist-plan-fidelity-forced
- **Severity**: minor
- **Concern**: Tests do not pin the step-5-resume and step-6-entry stale-env hygiene paths, so regressions there could reappear without a failing harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-forced: Address the concern above.

### FINDING_10 [OUT_OF_SCOPE]: Stale `_bg_wait_marker_context` baseline entry remains
- **Reviewer(s)**: cursor-specialist-plan-fidelity-forced
- **Severity**: minor
- **Concern**: The baseline still records the deleted `_bg_wait_marker_context` symbol, so the ratchet contains stale data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-forced: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0

