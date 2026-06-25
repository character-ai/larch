## Proposed Design Outline

### Goals
- Add a generic Codex/gpt-5.5 slot to both `/design` plan review and `/implement` code review on rounds 1 and 2.
- The slot uses `agents/code-reviewer.md` (full-scope reviewer, no archetype restriction) with model_role="default" (gpt-5.5 via existing LARCH_CODEX_MODEL env resolution).
- Wire per-slot `model_role` in `agent_waterfall.py` so the generic slot can use gpt-5.5 while the global `--model-role review` (gpt-5.4-mini) continues to govern all other Codex archetype slots.

### Non-goals
- No new agent file (reuse `agents/code-reviewer.md`).
- No new env var (existing LARCH_CODEX_MODEL covers model override for this slot).
- No change to rounds 3+ behavior (pruning, capping, etc.).
- No change to voter dispatch (generic slot is a reviewer slot only).

### Approach sketch
- Add `model_role: str = ""` to `Slot` dataclass in `agent_waterfall.py`; parse it from the manifest JSON; use `slot.model_role or opts.model_role` at Codex launch.
- In `plan_review_panel.py._static_slot_rows`: when `codex_slots=True` and `round_num <= 2`, append a "codex-plan-generic" slot with `agent=agents/code-reviewer.md` and `model_role="default"`.
- Extend `_slot_row` in `plan_review_panel.py` to accept an optional `model_role` kwarg and include it in the manifest row when non-empty.
- In `review_pipeline.py review_dispatch_panel`: when `codex_slots_available` and `round_num <= 2`, append a "generalist" Codex slot with `agent=agents/code-reviewer.md` and `model_role="default"`.
- Add regression tests in `test_agent_waterfall.py`, `test_plan_review_panel.py`, and `test_review_pipeline.py`.

### Surfaces in scope
- `python/agent_waterfall.py` — Slot dataclass + launch
- `python/plan_review_panel.py` — `_static_slot_rows`, `_slot_row`
- `python/review_pipeline.py` — `review_dispatch_panel`
- `python/test_agent_waterfall.py` — per-slot model_role tests
- `python/test_plan_review_panel.py` — generic slot round-gating tests
- `python/test_review_pipeline.py` — generalist slot round-gating tests

### Open questions
- None.
