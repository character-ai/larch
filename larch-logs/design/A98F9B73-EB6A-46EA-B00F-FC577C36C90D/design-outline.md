## Proposed Design Outline

### Goals
- Skip the guidelines block (keep invariants) in specialist-review and plan-review prompts when the run's applied difficulty is TRIVIAL or the diff mode is docs-only/generated-only.
- Thread difficulty explicitly via `--difficulty` flag through the render call chain for both renderer entry points.
- Update the specialist renderer's cache key so difficulty is part of the keyed input.

### Non-goals
- Do not change the design drafter or Gate C guideline payload.
- Do not add difficulty gating to voter prompts or aggregator prompts.
- Do not add env-based auto-discovery of difficulty inside the renderer (fail-open via empty flag default is sufficient).

### Approach sketch
- Add `difficulty: str = ""` param to `_architectural_guidelines_review_section()` in `rendering.py`. When `normalize_tier(difficulty) == "TRIVIAL"`, return only the invariants block.
- Add `--difficulty ""` to `_parse_specialist` and `render_plan_review_main` parsers. For docs-only/generated-only, gate guidelines in specialist path (diff_mode already in cache key, no additional key change needed).
- Pass `--difficulty {tier}` from `plan_review_panel.py`'s three render subprocess callers.
- Thread `--difficulty {tier}` from `review_dispatch_panel.py` through `waterfall_args`, then through `Options`/`_common_args` in `agent_waterfall.py`, then into `_review_specialist_render_args` in `_review_launcher.py`.
- Add `difficulty={resolved_difficulty}` to the specialist renderer cache `key_input`.

### Surfaces in scope
- `python/larch/rendering/rendering.py`
- `python/larch/review/plan_review_panel.py`
- `python/larch/review/review_dispatch_panel.py`
- `python/larch/agents/agent_waterfall.py`
- `python/larch/agents/_review_launcher.py`
- `python/tests/rendering/test_rendering.py`

### Open questions
- None.
