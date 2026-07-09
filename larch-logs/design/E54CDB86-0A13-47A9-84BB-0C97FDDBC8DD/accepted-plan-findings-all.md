### FINDING_1: Update static slot-count expectations
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The plan does not explicitly update the generic Codex static-slot-count tests that still encode the removed additive lane, so a narrow change can land with failing coverage around `STATIC_SLOT_COUNT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add explicit updates in the plan for those two tests (7→6 and 4→3) and rename test_dispatch_panel_codex_unavailable_keeps_cursor_auto_lane to assert three cursor specialists with cursor_model/resolved_model auto instead of plan-fidelity-auto


### FINDING_3: Map forced fallback to architecture
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: major
- **Concern**: The retained `plan-fidelity-forced` row has no focus-area mapping, so the supported fallback lane can be misbucketed as code-quality instead of architecture in yield/classification output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add `"plan-fidelity-forced": "architecture"` to `_static_focus_area`, or make `_write_archetype_map` honor the row's explicit `focus_area` for forced outputs.
  - From Codex-Requirements: Add `plan-fidelity-forced: architecture` to `_static_focus_area`, or preserve the row's explicit `focus_area` when the static slug is unrecognized.


