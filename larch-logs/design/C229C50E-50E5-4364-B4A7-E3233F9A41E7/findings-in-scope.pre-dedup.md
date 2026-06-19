### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: python/design_lifecycle.py:36-82
- **Concern**: Warning propagation omits PHASE_RESULT_ENV_ALLOW_KEYS update. Scenario: plan_review.step3_loop_persist_envelope writes via phase_driver_write_result_env which rejects any key outside PHASE_RESULT_ENV_ALLOW_KEYS; once DEGRADED_PANEL_WARNING is copied into round values and persisted the Step 3 loop raises ValueError and aborts after a degraded panel dispatch
- **Proposed resolution**: Add ### UPDATED: python/design_lifecycle.py to the plan; include DEGRADED_PANEL_WARNING in PHASE_RESULT_ENV_ALLOW_KEYS; extend design_lifecycle allowlist coverage if needed



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:43-53 vs plan.txt:207-208
- **Concern**: Contradictory drop rules for bad JSON and non-dict rows under --skip-invalid-slots. Scenario: The agent_waterfall section says preserve existing hard fail on bad JSON and non-dict rows while edge cases say skip them with the flag; an implementer may still abort the whole panel on the first malformed line
- **Proposed resolution**: Clarify that hard fail applies only when skip_invalid_slots is false; under the flag those rows are collected into InvalidSlotDrop and skipped



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:36-82
- **Concern**: Plan persists DEGRADED_PANEL_WARNING via step3_loop_persist_envelope but never adds the key to PHASE_RESULT_ENV_ALLOW_KEYS. Scenario: phase_driver_write_result_env raises ValueError(result env key is not allowlisted: DEGRADED_PANEL_WARNING) on the first degraded round; Step 3 loop aborts and the operator never gets the warning at the production boundary
- **Proposed resolution**: Add ### UPDATED: python/design_lifecycle.py: append DEGRADED_PANEL_WARNING to PHASE_RESULT_ENV_ALLOW_KEYS (and a focused persist test if the harness exercises allowlist keys)



### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/plan_review.py:1252-1277,1360-1367
- **Concern**: Step 3 loop never carries round-level DEGRADED_PANEL_WARNING into final envelope values. Scenario: On the default auto-apply path (loop_status=complete, accepted>0), round values get DEGRADED_PANEL_WARNING from execute_round, but only zero-findings-degraded-panel copies values into degraded_values; final complete_values stays {} and step3_loop_emit_envelope/persist omit the warning from .step3-review-result.env despite the plan’s end-to-end propagation claim (wrapper stdout overlay may still bind it)
- **Proposed resolution**: When panel_kv carries DEGRADED_PANEL_WARNING, stash it (e.g. merge into degraded_values or a round-scoped sidecar) before awaiting-apply; merge into complete_values at awaiting-continuation; add step3_loop_emit_envelope emission; extend the propagation test to exercise run_step3_review complete path not only direct persist helpers



### FINDING_5:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:24-63
- **Concern**: `DEGRADED_PANEL_WARNING` is planned for `.step3-review-result.env`, but the result-env writer allowlist is not updated. Scenario: When `step3_loop_persist_envelope` writes the new key, `phase_driver_write_result_env` rejects it as not allowlisted and Step 3 can fail instead of degrading gracefully
- **Proposed resolution**: Add `DEGRADED_PANEL_WARNING` to `PHASE_RESULT_ENV_ALLOW_KEYS` and keep the planned envelope test



