### OOS_1:
- **Description**: Offline harness is not wired into make lint or relevant-checks.sh. Scenario: The plan adds scripts/test-implement-preflight.sh but only optionally mentions Makefile/docs wiring. Without a shard target or relevant-checks case, edits to implement-preflight.sh may not run the new harness in CI even though acceptance requires those four cases.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: Makefile:6-106
- **Phase**: design

### OOS_1:
- **Description**: Contract and harness prose claim "exact admission refusal templates" (plural), but only the `managed-prefix` branch gets partial substring asserts; `has-blockers`, `audit-report-label`, `report-title`, and `ADMISSION_ERROR` templates are unpinned.. Scenario: Admission refusal wording for non-`managed-prefix` branches can regress without any harness failure; feature still ships for the one tested branch.
- **Reviewer**: Cursor-dyn-harness-pin-coherence
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/implement-preflight.md:253-262 vs scripts/test-implement-preflight.sh:320-327
- **Phase**: design

### OOS_2:
- **Description**: Plan adds `preflight-helper` but does not retarget the awk-violation error text still saying "preflight plan-block read".. Scenario: Misleading CI failure text if a future edit adds awk fallback to the helper fence.
- **Reviewer**: Cursor-dyn-harness-pin-coherence
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-fence-shape.sh:94-95
- **Phase**: design

