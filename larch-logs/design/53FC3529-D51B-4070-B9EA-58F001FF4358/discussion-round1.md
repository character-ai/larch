## Decision 1: New shared dispatch module location
- **Question**: Where should `python/larch/review/dispatch_shared.py` live?
- **Resolution**: `python/larch/review/dispatch_shared.py` — follows `review_pipeline_shared.py` naming; `agent_voters.py` already imports from `larch.review`.
- **Source**: user (Step 1c)

## Decision 2: DispatchState path field type
- **Question**: Should `DispatchState.voter_*_path` fields use `str` or `Path`?
- **Resolution**: `Path` — type-safe; `agent_voters.py` callers convert with `str()` at their boundary.
- **Source**: user (Step 1c)

## Decision 3: Canonical _resolved_model_for_row signature
- **Question**: Which of the three `_resolved_model_for_row` copies is canonical?
- **Resolution**: 3-arg form `(tool: str, model_role: str = "", default_model: str = "")` as in `review_dispatch_panel.py` and `plan_review_panel.py`. `agent_voters.py`'s 2-arg copy is the drifted one (hardcodes `codex_role="vote"`).
- **Source**: codebase (acceptance criterion says "canonical `model_role` signature")

## Decision 4: Topology key parameterisation
- **Question**: What does "slot-row builders parameterized by topology key" mean?
- **Resolution**: Slot-row builders in the shared module accept a `topology_key: str` argument (e.g., `"review.voters"` vs `"design.plan_voters"`) passed to `external_defaults.voter_policies()` / `external_defaults.slot_defaults()`.
- **Source**: codebase

## Decision 5: _emit_final_kvs implementation mechanism
- **Question**: Should the shared emitter call `cli.py voting voter-status-block` (subprocess) or emit KVs inline via `logging_util.emit_kv`?
- **Resolution**: Delegate to `cli.py voting voter-status-block` (subprocess), matching `plan_review_panel.py`. `agent_voters.py`'s inline form is the drifted copy.
- **Source**: codebase

## Decision 6: Tally, snapshot family, broader unification out of scope
- **Question**: Are `review_tally.py`/`plan_review_tally.py` consolidation and `snapshot.py` parameterisation in scope?
- **Resolution**: No. This is partition piece 1 of 3; tally and snapshot are pieces 2 and 3.
- **Source**: issue description
