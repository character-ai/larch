# Review Round 1

- Mode: `diff`
- 11 accepted, 4 rejected (2 neutral)

## Accepted Findings

### FINDING_2: Authored outcome validation is missing from handled-state detection
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-gate-authority
- **Severity**: minor
- **Concern**: `_already_handled` accepts vocabulary-valid `ASSESSMENT_KIND` metadata without validating prose consistency. A clean metadata value paired with identifier-bearing non-clean prose can be reported as handled/complete instead of requiring reassessment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-gate-authority: For `NOTE_STATE_AUTHORED`, require `_authored_outcome_valid(note=…, outcome=metadata["ASSESSMENT_KIND"], invariant=…)` (or call the shared validator) before returning `True` from `_already_handled`; treat mismatch like missing metadata and leave the kind pending for `re-author-required`.


### FINDING_3: Repair path can rewrite malformed authored outcomes as handled
- **Reviewer(s)**: dyn-dyn-gate-authority
- **Severity**: minor
- **Concern**: `_repair_current_outcome` can trust vocabulary-valid durable metadata when the note prose fails the clean-claim validation, rewrite the outcome sidecar, and return handled instead of requiring re-authoring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-gate-authority: After loading the note text, run the shared authored-outcome validation; on clean-claim mismatch return `config.ASSESSMENT_RESULT_REAUTHOR_REQUIRED` without writing a consumable sidecar.


### FINDING_4: Unavailable handling can preserve invalid or stale violation evidence
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-gate-authority
- **Severity**: major
- **Concern**: Violation preservation can rely on metadata or a sidecar without fully validating current-head/base identity, outcome pins, and note consumability. This can preserve stale, identity-drifted, or metadata-only violation evidence and bypass unavailable/reassessment routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Require durable metadata `ASSESSMENT_KIND=violation` plus sidecar/identity validation before preserving.
  - From dyn-dyn-gate-authority: Preserve only when `invariant_note_consumable(...)`, metadata `ASSESSMENT_KIND=violation`, and the invariant ship outcome sidecar validates for the current head/base; otherwise do not short-circuit the unavailable write.


### FINDING_5: Re-author exceptions are uncaught in retained staged-assessment paths
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-gate-authority
- **Severity**: major
- **Concern**: `refresh_staged_assessment_for_current_head` can raise `AssessmentReauthorRequired` for invalid or missing staged metadata, but catches only I/O/decode exceptions. The result can be an unbounded exception instead of bounded reassessment routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Catch AssessmentReauthorRequired and return False; add legacy sidecar regression tests.
  - From dyn-dyn-gate-authority: Catch `AssessmentReauthorRequired` explicitly and return `False` (or surface a dedicated status) without pinning; add regression coverage for staged sidecars with empty/invalid `ASSESSMENT_KIND`.


### FINDING_6: Live-diff pinning has the same uncaught re-author exception
- **Reviewer(s)**: dyn-dyn-gate-authority
- **Severity**: minor
- **Concern**: `_pin_note_from_live_diff` can abort with an uncaught `AssessmentReauthorRequired` while re-stamping invalid staged metadata instead of failing closed and routing upstream callers to reassessment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-gate-authority: Catch `AssessmentReauthorRequired`, leave pinning at `False`, and ensure upstream ship/report callers route to reassessment instead of treating the failure as a generic I/O error.


### FINDING_7: Re-author results lack a bounded reason/detail
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The coordinator discards the specific re-author exception reason, and Step 8 envelopes do not carry per-kind reason/detail. Operators cannot distinguish clean-claim mismatch from missing or invalid outcome metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Carry a sanitized bounded per-kind reason/detail through coordinator output and the Step 8 result and merge envelopes, including rejoin output.


### FINDING_8: Step 8 harness lacks coordinator and terminal re-author regression coverage
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The coordinator and Step 8 harness lack coverage for re-author persistence, artifact cleanup, terminal status, no-retry behavior, reassessment routing, preserved envelopes, and no-ship behavior. Regressions could map malformed authored assessments to unavailable, retry, completion, or ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add the plan table-driven coordinator tests and stdout contract assertions.
  - From cursor-specialist-testing: Add harness cases register Makefile target and CI shard entry.
  - From codex-specialist-testing: Add tests for mismatch and invalid outcomes, identifier-free non-clean outcomes, legacy repair, artifact cleanup, and distinct true-unavailable behavior.
  - From codex-specialist-testing: Add Step 8 harness cases for terminal persistence, BGJOB_RC=0, reassessment routing, no retry or ship, and matching rejoin without a new bgjob.


### FINDING_9: Step 8 harness needs fresh and rejoin terminal-envelope cases
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The Step 8 harness does not verify fresh and rejoin `re-author-required` terminal envelopes, no attempt-2 retry, `BGJOB_RC=0`, preserved results, or absence of ship handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add stubbed-child tests for fresh and rejoin re-author terminal envelopes.
  - From codex-specialist-edge-cases: Add fresh and rejoin tests that assert status, BGJOB_RC=0, no attempt 2, preserved results, and no ship handoff.
  - From cursor-specialist-testing: Add harness cases for emit-reauthor, BGJOB_RC=0, and no attempt-2 retry.
  - From codex-specialist-testing: Add Step 8 harness cases for terminal persistence, BGJOB_RC=0, reassessment routing, no retry or ship, and matching rejoin without a new bgjob.


### FINDING_10: Ship-routing regression tests for legacy metadata are missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Ship tests update fixtures but do not cover legacy notes lacking `ASSESSMENT_KIND`, unavailable-negative routing, or explicit-outcome/prose routing through `_read_current_*` paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add needs_assessment unavailable-negative and explicit-outcome routing tests for _read_current paths.


### FINDING_12: Present-state reference documentation omits the re-author terminal contract
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Present-state implementation references still describe complete-only Step 8 success and can contradict the new `re-author-required` terminal behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Update reference to document re-author-required alongside complete.
  - From cursor-specialist-testing: Update present references and add harness pins for re-author-required routing.


### FINDING_17: Implement skill routing prose has overlapping failure rules
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The skill text contains overlapping complete-only failure and re-author carve-out rules, which could cause an orchestrator to route `re-author-required` as a tool failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Reconcile the two paragraphs so only one routing rule applies per status.
