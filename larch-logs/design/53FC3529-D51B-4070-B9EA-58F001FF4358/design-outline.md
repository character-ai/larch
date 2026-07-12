## Proposed Design Outline

### Goals
- Create `python/larch/review/dispatch_shared.py` with a single canonical `DispatchState`, `_resolved_model_for_row`, `_fresh_calibration_stats_file`, `_emit_final_kvs`, and parse-rate retry helper.
- Remove three diverged copies of `_resolved_model_for_row` and two copies of `DispatchState`/`_emit_final_kvs`; both families import from the shared module.
- Achieve net line reduction; ensure all four acceptance-criterion test suites pass unchanged.

### Non-goals
- Tally unification (`review_tally.py` / `plan_review_tally.py`) — piece 2.
- Snapshot family parameterization (`snapshot.py`) — piece 3.
- Broader `review_dispatch_panel.py` refactor beyond voter dispatch.

### Approach sketch
- Add `python/larch/review/dispatch_shared.py`: `DispatchState` with `Path` voter paths, `_resolved_model_for_row(tool, model_role, default_model)`, `_fresh_calibration_stats_file(tmpdir)`, `_emit_final_kvs`, `_run_parse_rate_retry`.
- `agent_voters.py`: delete local duplicates, import from `dispatch_shared`; adapt `str()` casts at boundary.
- `plan_review_panel.py` (voter half): delete local `DispatchState`, `VoterPromptResult`, `_resolved_model_for_row`, `_fresh_calibration_stats_file`, `_emit_final_kvs`; import from `dispatch_shared`.
- `review_dispatch_panel.py`: delete local `_resolved_model_for_row`; import from `dispatch_shared`.
- Add `python/tests/review/test_dispatch_shared.py` covering the shared helpers.

### Surfaces in scope
- `python/larch/review/dispatch_shared.py` (new)
- `python/larch/agents/agent_voters.py`
- `python/larch/review/review_dispatch_panel.py`
- `python/larch/review/plan_review_panel.py`
- `python/tests/review/test_dispatch_shared.py` (new)

### Open questions
- None.
