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
