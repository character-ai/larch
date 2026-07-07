### FINDING_1: Add specialist prompt wiring for reviewer-plan-fidelity
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The new reviewer-plan-fidelity lane can be launched without plan context on description-mode and diff shapes that currently bypass the plan embed, so the review will misfire on missing-plan rather than checking plan fidelity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/larch/rendering/rendering.py: extend include_context in _specialist_payload_bytes and _render_specialist_text to treat agent_base reviewer-plan-fidelity like reviewer-testing whenever plan_file or feature_file is present; add a focused rendering test


### FINDING_2: Persist per-slot Cursor model in static manifest rows
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Panel Contract
- **Severity**: major
- **Concern**: Static review-manifest rows do not persist per-slot cursor_model, so agent_waterfall cannot forward the override and the new Cursor/auto lane falls back to the global Cursor model/composer telemetry instead of staying pinned to auto.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the static-row loop, when slot.cursor_model is set, add cursor_model to the manifest row; keep resolved_model=auto for that row so _with_attribution does not derive composer from env
  - From Cursor-Pragmatic: When emitting each static row, copy slot.cursor_model into the manifest dict when non-empty. Keep explicit resolved_model=auto for plan-fidelity-auto so _with_attribution does not inherit composer-2.5 from resolve_model_args.
  - From Codex-Pragmatic: Add cursor_model=config.CURSOR_AUTO_MODEL to the new static row in review_dispatch_panel and pass that field through to agent launch-review.
  - From Cursor-Requirements: In _append_static_specialist_rows (and _append_manifest_row callers as needed), copy SlotDefault.cursor_model into manifest rows for Cursor slots; keep resolved_model auto on the new row
  - From Codex-Requirements: Include cursor_model in the JSON row for the new static reviewer and keep resolved_model pinned to auto for that row.
  - From Cursor-dyn-Panel Contract: In _append_static_specialist_rows, when slot.cursor_model is set on a Cursor row, include cursor_model in the manifest dict (alongside explicit resolved_model=auto for plan-fidelity-auto)


### FINDING_3: Persist Cursor model through retry metadata and replay
- **Reviewer(s)**: Codex-Arch, Cursor-dyn-Panel Contract
- **Severity**: major
- **Concern**: Retry metadata/replay drops the resolved Cursor model, so a failed Cursor row relaunches with the default Composer model and changes both cost classification and A/B telemetry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add an OUTER_LAUNCHER_CURSOR_MODEL field, parse it in RetryMeta, and pass --cursor-model through _launch_outer_retry for Cursor retries
  - From Cursor-dyn-Panel Contract: Extend _review_append_outer_meta to persist the resolved Cursor model (e.g. OUTER_LAUNCHER_CURSOR_MODEL=auto); teach collect_results review retry to forward --cursor-model when present; add a focused collect_results or launch-review retry test


### FINDING_4: Forward per-slot cursor-model on Cursor launches
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Even if the manifest carries a per-slot override, _launch_slot still drops it when building argv, so Cursor tools continue to resolve through the global model path instead of the slot's override.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: The new lane keeps using resolve_model_args / LARCH_CURSOR_MODEL and the auto-vs-composer experiment fails Extend Slot / _parse_slot_row for cursor_model and, in _launch_slot, append --cursor-model when tool is cursor and the slot carries a non-empty override


### FINDING_5: Map plan-fidelity-auto to plan-fidelity in focus-area classification
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: minor
- **Concern**: The static focus-area classifier knows plan-fidelity but not the new plan-fidelity-auto slug, so filenames for the new lane can fall through to the wrong scoreboard/classification bucket.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Scoreboard and classification mislabel the new reviewer, undermining auto vs composer comparison Add plan-fidelity-auto (or an equivalent suffix alias) mapping to the same focus area as plan-fidelity
  - From Cursor-Requirements: Add plan-fidelity-auto (or alias stripping -auto) to _static_focus_area with architecture (or the chosen focus_area from config)


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


