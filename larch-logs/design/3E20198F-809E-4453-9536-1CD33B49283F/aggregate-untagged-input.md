### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/final_report.py:234-243
- **Concern**: Persisted drop notice still masks stale-note invalidation. Scenario: If a stale `DROPPED_NOTE_ARTIFACT` already exists, step 6 sets `section` from `read_dropped_note_notice()` and step 8 never runs. A consumable but fingerprint-stale durable note will keep showing the old drop notice and will not be invalidated, so the recovery path the plan says to preserve is still broken.
- **Proposed resolution**: Move the persisted-drop-notice read after the `has_guideline_artifacts and (not consumable or stale)` branch, or gate notice rendering on `not stale`, so stale-note invalidation can run even when a marker is already present.

### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/final_report.py:234-243
- **Concern**: Persisted drop notice is checked before the stale-note invalidate branch.. Scenario: If an old DROPPED_NOTE_ARTIFACT is still present and the durable note is consumable but stale, step 6 fills section from the notice, so step 8 never runs. That leaves the stale durable note and sidecar in place, which contradicts the plan’s promise to preserve the stale-fingerprint invalidation path.
- **Proposed resolution**: Move the drop-notice read behind the consumable-but-stale invalidation branch, or gate it so an existing notice cannot short-circuit invalidate when stale is true.

### FINDING_3:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/final_report.py:234-243
- **Concern**: Persisted drop notices still preempt stale-note invalidation. Scenario: When a consumable note is stale and an old `DROPPED_NOTE_ARTIFACT` already exists, step 6 formats that marker before step 8 can run, so `_persist_drop_notice_and_invalidate()` never fires and the stale durable note survives. That breaks the plan's stated requirement to preserve the stale-fingerprint invalidation path.
- **Proposed resolution**: Move the persisted-drop-notice read behind the stale invalidation branch, or explicitly bypass and clear any existing drop marker whenever `stale` is true so stale notes still invalidate even if a marker is present.
