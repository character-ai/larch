### OOS_1: [OUT_OF_SCOPE] Recorder/gate drift from the shared allowlist
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: `STEP3_ESCALATION_FAILURE_STATUSES` is still the shared allowlist, but `step3_record_report_evidence` keeps a hand-maintained phase map, so config-only additions could be counted by the report gate without ever being recorded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Gate on `status in STEP3_ESCALATION_FAILURE_STATUSES` and use a single phase="validation" for all allowlisted statuses
  - From cursor-specialist-testing: derive the phase map from `STEP3_ESCALATION_FAILURE_STATUSES` (e.g. `{s: "validation" for s in ...}`) or add a parametrized pytest that every allowlisted status reaches `subprocess.run`

### OOS_2: [OUT_OF_SCOPE] Handoff skip remains routed through the early return
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The normal handoff statuses still reach `step3_loop_emit_envelope`, so the no-op now depends on the trimmed phase map and `phase is None` early return while `_STEP3_INTERACTIVE_STATUSES` and `_STEP3_NEXT_ACTION_BY_STATUS` remain untouched; regression coverage needs to keep proving the skip path and mixed/fallback artifacts stay inert.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Broad substring matching can misread panel failure evidence
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `panel_failure_evidence_present` still uses broad substring regex matching on ledger files, so incidental substrings in unrelated log fields can trip panel-failure retry behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Legacy marker can still force escalation-success
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `escalation_evidence_present()` still treats any non-empty `design-failure-escalation-record-failure.env` as evidence, so a resumed tmpdir with a stale marker and a handoff-only ledger can still file `escalation-success`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: only if product wants stricter behavior later; add a marker-only negative test or gate the marker branch on filtered ledger/fallback content.

