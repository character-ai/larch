### [Plan Review] FINDING_1

### FINDING_1: Missing forced plan-fidelity timing kinds
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: minor
- **Concern**: The timing allowlist drops the deleted auto-only plan-fidelity kinds but does not add the surviving forced plan-fidelity kinds, so forced-row launches can still record unknown timing kinds and warn on every run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: "Add the forced-row timing kinds that the launcher will emit, or retarget the forced row to an already-allowlisted kind."
  - From Codex-Innovation: "Add the forced phase1 kinds to `TIMING_TASK_KINDS_ALLOWED` and keep the auto entries removed."


### [Plan Review] FINDING_2

### FINDING_2: Keep cursor_model and resolved_model aligned in Cursor row builders
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The Cursor manifest builders duplicate `resolved_model=auto` instead of teaching `_with_attribution` to derive `resolved_model` from an existing `cursor_model`, which leaves a launch-vs-attribution mismatch if any call site is missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: "In both _with_attribution helpers, when tool is cursor and row already has a non-empty cursor_model, set resolved_model from cursor_model before the resolve_model_args fallback; then manifest builders only need cursor_model=config.CURSOR_AUTO_MODEL (or slot.cursor_model) and forced-row cursor_model=auto, dropping repeated resolved_model assignments and paired test assertions except where launch attribution is explicitly overridden"

