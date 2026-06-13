## Proposed Design Outline

### Goals
- Port 6 bash scripts (validate-citations, render-findings-batch, run-research-planner, compute-research-banner, validate-research-output, eval-research) to Python modules under `python/`.
- Register CLI verbs in `python/cli.py`; cut all call-sites to direct `cli.py` calls.
- Replace all 8 bash test harnesses with pytest; delete absorbed bash + md siblings.

### Non-goals
- Dialectic scope (`dialectic-smoke-test.sh`, `make smoke-dialectic`): dropped entirely.
- New features beyond behavior-preserving port.
- Changing the contract surfaces of the ported scripts.

### Approach sketch
- Two new modules: `python/research.py` (validate-citations, render-findings-batch, run-research-planner, compute-research-banner) and `python/research_eval.py` (validate-research-output, eval-research).
- Reuse B4 `agents.py` for planner-launch patterns; reuse B6 `rendering.py` for findings-batch render logic.
- Register `("research", "<verb>")` and `("eval", "<verb>")` entries in `_REGISTRY`.
- Cut all .md call-sites in research SKILL.md and references; update Makefile targets; remove `make smoke-dialectic` from `docs/linting.md`.
- Pytest: `python/test_research.py` and `python/test_research_eval.py` covering all 8 former bash harnesses.

### Surfaces in scope
- `python/research.py` (new)
- `python/research_eval.py` (new)
- `python/test_research.py` (new)
- `python/test_research_eval.py` (new)
- `python/cli.py` — new registry entries
- `skills/research/scripts/` — delete 4 sh + md + test sets
- `scripts/` — delete 2 sh + md + test sets
- `docs/linting.md` — remove `make smoke-dialectic` row
- `python/migrated-scripts.tsv` — 6 new entries
- All .md call-sites (research SKILL.md, references/, scripts/)

### Open questions
- None.
