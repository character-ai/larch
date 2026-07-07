### FINDING_1: Plan-fidelity context omitted on docs-only diffs
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: The plan-fidelity reviewer can be launched with a readable plan file but without embedded `<implementation_plan>` context on docs-only, test-only, or generated-only diffs, causing it to misfire with missing-plan findings instead of performing the intended plan-fidelity review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `_specialist_payload_bytes` and `_render_specialist_text`, add a separate rule: when `agent_base == "reviewer-plan-fidelity"` and `args.plan_file` or `args.feature_file` is present, set `include_context` true regardless of `args.mode` or `diff_mode`. Keep the existing reviewer-testing and diff+generic rules unchanged. Extend the planned rendering test with a `diff` + `docs-only` case that asserts the blocks are embedded.


### FINDING_2: Cursor auto constant defined too late
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: The new SlotDefault for the review panel appears to reference `CURSOR_AUTO_MODEL` before that constant is defined in `python/larch/core/config.py`, which would raise during import and block review/implement commands from loading config.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Move CURSOR_AUTO_MODEL above ROLE_DEFAULTS and reference CURSOR_AUTO_MODEL, or use the literal "auto" for the slot
  - From Codex-Requirements: Move CURSOR_AUTO_MODEL above ROLE_DEFAULTS and reference it unqualified, or use the literal "auto" in the slot while keeping tests against the constant


