## Proposed Design Outline

### Goals
- Plan-review panel survives one invalid slot row: drop the bad row, launch the rest.
- Record each dropped row as a visible degraded-panel warning, not a silent skip.
- Preserve fail-closed behavior for every other `dispatch-waterfall` consumer.

### Non-goals
- No change to voters (`dispatch_voters`), `/review`, the aggregator, or the decompose panel.
- No dropping of structurally-valid-but-unrenderable rows (a row whose `prompt_file` points at a missing/empty file still loads).
- No new behavior when zero valid slots remain: `_load_slots` still raises (fail closed).

### Approach sketch
- Add an opt-in `--skip-invalid-slots` flag to `agent dispatch-waterfall`; thread it into `_load_slots`.
- `_load_slots(..., skip_invalid=True)`: collect per-row validation errors, skip bad rows, continue; raise only when no valid slot remains.
- `dispatch_panel` (`python/plan_review_panel.py`) passes `--skip-invalid-slots` and surfaces a degraded-panel warning naming each dropped slot.
- Default callers stay byte-for-byte fail-closed: no flag means raise on the first bad row, exactly as today.

### Surfaces in scope
- `python/agent_waterfall.py`: `_load_slots`, `Options`, the `dispatch-waterfall` argparser, `dispatch_waterfall`.
- `python/plan_review_panel.py`: `dispatch_panel` subprocess invocation plus drop-warning surfacing.
- `python/test_agent_waterfall.py`, `python/test_plan_review_panel.py`: mixed valid/invalid manifest tests; keep `test_load_slots_validation_rejects_bad_rows` green.

### Open questions
- How to surface the per-drop warning: reuse the existing `.dropped-slots` sidecar / KV warning pattern in `dispatch_waterfall`, or emit a panel-level KV from `dispatch_panel`. Resolve during plan drafting from the existing degraded-panel conventions.
