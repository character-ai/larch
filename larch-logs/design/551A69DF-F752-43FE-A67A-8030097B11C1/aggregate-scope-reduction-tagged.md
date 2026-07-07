### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/review/review_dispatch_panel.py:241-246
- **Concern**: [SCOPE-REDUCTION] Parallel cursor_model plumbing duplicates manifest resolved_model. Scenario: The plan adds cursor_model through SlotDefault, manifest rows, Slot parsing, --cursor-model on launch-review, and OUTER_LAUNCHER_CURSOR_MODEL replay, while also setting explicit resolved_model=auto on the plan-fidelity-auto row. Dispatch already writes resolved_model via _with_attribution and only fills it when absent, so a second override channel adds cross-layer surface without a separate contract need.
- **Proposed resolution**: Collapse the override to one field: set resolved_model=auto on the plan-fidelity-auto manifest row, parse that value in agent_waterfall._parse_slot_row / Slot, launch Cursor with --model from resolved_model when it differs from the global Cursor default, and replay the same value through retry metadata. Drop SlotDefault.cursor_model, manifest cursor_model, and the public --cursor-model flag unless an operator-facing override is required.
