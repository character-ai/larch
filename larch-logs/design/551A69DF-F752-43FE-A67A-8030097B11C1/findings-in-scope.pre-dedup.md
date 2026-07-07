### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/review/review_dispatch_panel.py:241-246
- **Concern**: [SCOPE-REDUCTION] Parallel cursor_model plumbing duplicates manifest resolved_model. Scenario: The plan adds cursor_model through SlotDefault, manifest rows, Slot parsing, --cursor-model on launch-review, and OUTER_LAUNCHER_CURSOR_MODEL replay, while also setting explicit resolved_model=auto on the plan-fidelity-auto row. Dispatch already writes resolved_model via _with_attribution and only fills it when absent, so a second override channel adds cross-layer surface without a separate contract need.
- **Proposed resolution**: Collapse the override to one field: set resolved_model=auto on the plan-fidelity-auto manifest row, parse that value in agent_waterfall._parse_slot_row / Slot, launch Cursor with --model from resolved_model when it differs from the global Cursor default, and replay the same value through retry metadata. Drop SlotDefault.cursor_model, manifest cursor_model, and the public --cursor-model flag unless an operator-facing override is required.



### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/rendering/rendering.py:913-959
- **Concern**: Plan-fidelity rendering still mirrors reviewer-testing and only embeds plan context in description mode or generic diff. Scenario: `review dispatch-panel` requires a readable `--plan-file` on every `/review` and `/implement` Step 5 launch, but `classify-diff` often returns `docs-only`, `test-only`, or `generated-only`. On those paths `include_context` stays false, so `reviewer-plan-fidelity` is launched with `--plan-file` yet its prompt omits `<implementation_plan>`. The agent then emits a false Major missing-plan finding instead of plan-fidelity review, wasting the new lane and polluting votes.
- **Proposed resolution**: In `_specialist_payload_bytes` and `_render_specialist_text`, add a separate rule: when `agent_base == "reviewer-plan-fidelity"` and `args.plan_file` or `args.feature_file` is present, set `include_context` true regardless of `args.mode` or `diff_mode`. Keep the existing reviewer-testing and diff+generic rules unchanged. Extend the planned rendering test with a `diff` + `docs-only` case that asserts the blocks are embedded.



### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/config.py:360-383
- **Concern**: Plan references config.CURSOR_AUTO_MODEL inside config.py for the new SlotDefault. Scenario: The review.panel registry is evaluated before CURSOR_AUTO_MODEL is defined at module bottom, and config.py has no config binding, so following the plan literally makes importing larch.core.config fail
- **Proposed resolution**: Move CURSOR_AUTO_MODEL above ROLE_DEFAULTS and reference CURSOR_AUTO_MODEL, or use the literal "auto" for the slot



### FINDING_4:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/config.py:360-378
- **Concern**: Cursor auto slot references CURSOR_AUTO_MODEL before it exists. Scenario: ROLE_DEFAULTS is constructed before CURSOR_AUTO_MODEL is defined later in config.py; using config.CURSOR_AUTO_MODEL or CURSOR_AUTO_MODEL in the new SlotDefault raises at import time, so review and implement commands cannot load config
- **Proposed resolution**: Move CURSOR_AUTO_MODEL above ROLE_DEFAULTS and reference it unqualified, or use the literal "auto" in the slot while keeping tests against the constant



