### [Plan Review] FINDING_2

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agent_waterfall.py:639-782
- **Concern**: Fail-closed sidecar write aborts dispatch when valid slots remain. Scenario: Plan Failure modes require ValidationError when the invalid-slot sidecar cannot be written. That repeats the #4765 blast radius: one ancillary I/O failure blocks every valid reviewer from launching.
- **Proposed resolution**: Log drops in memory; emit single-line INVALID_SLOT_* / DEGRADED_PANEL_WARNING KVs; treat sidecar write failure as warn-only (or omit the sidecar).




