## Proposed Design Outline

### Goals
- Reduce Step 8 relaunch count by one: when both assessments are needed, exit once with a combined reason instead of twice.
- Keep all artifact schemas, PR-body sections, and outcome sidecars byte-compatible.
- Preserve back-compat for runs paused on the old per-kind `NEXT_ACTION` tokens.

### Non-goals
- Do not merge the two durable-note schemas or write wrappers.
- Do not change Phase A staging, conflict-fix paths, or CI-fix no-rerun constraints.
- Do not create a new merged reference file; cross-link only.

### Approach sketch
- In `ship.py` (`_refresh_guidelines_gate_after_rebase` and `run_ship` compose block): run both gates before any early exit; if either needs assessment, return one `ShipResult(needs_user_reason="architectural-assessments", detail=<comma-separated kinds>)` with a single `_write_ship_state(phase="assessments")` call.
- In `dispatch_ship.py`: add `"architectural-assessments"` → `"assessments"` mapping; keep old per-kind mappings.
- In `ship_resume.py`: add `"assessments"` to the pre-PR-compose resume set.
- In `SKILL.md` lines 679-680: add `assessments` handler before the old back-compat handlers.
- In `ship-pr-exit-matrix.md` and the two present-reference files: document the combined token and cross-link.

### Surfaces in scope
- `python/larch/implement/ship.py`
- `python/larch/implement/ship_resume.py`
- `python/larch/implement/dispatch_ship.py`
- `skills/implement/SKILL.md`
- `skills/implement/references/ship-pr-exit-matrix.md`
- `skills/implement/references/architectural-invariants-present.md`
- `skills/implement/references/architectural-guidelines-present.md`
- `python/tests/implement/test_ship.py`
- `python/tests/implement/test_implement_dispatch.py`
- `skills/implement/scripts/test-architectural-guidelines-step.sh`

### Open questions
- None.
