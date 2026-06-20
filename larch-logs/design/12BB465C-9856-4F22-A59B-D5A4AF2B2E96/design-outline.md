## Proposed Design Outline

### Goals
- Fix #4886: a clean no-issues reviewer whose `{"no_issues_found": true}` sentinel follows narration is recovered as a clean pass, not dropped as `NOT_SUBSTANTIVE`.
- Fix #4888: reviewer launch-failure logs use a caller-derived site label so launch and collector failures for the same panel agree.

### Non-goals
- Do not weaken the strict zero-preamble gate for findings output.
- Do not change reviewer prompts (`rendering.py`) or `/research`'s own validation path.
- Do not add a Codex-only normalizer (none exists; the shared validator covers Codex).

### Approach sketch
- `research_eval.py::validate_structured_reviewer_output`: after structured parse yields nothing, salvage a clean pass only when exactly one standalone sentinel line is present; emit a low-severity, non-failure warning.
- `agents.py::_review_cursor_normalize_no_issues`: collapse a standalone trailing sentinel (not just the first line), keeping the `schema_version` findings guard.
- `agents.py`: thread a caller `site` into `_review_append_launch_failure` via a new `agent launch-review --site`; normalize the sibling `_append_implement_launch_failure` site `"2"` -> `"implement Step 2"`.
- `collect_results.py`: surface the recovered-pass warning without classifying the slot `NOT_SUBSTANTIVE`.

### Surfaces in scope
- `python/research_eval.py`, `python/agents.py`, `python/collect_results.py`, plan-review panel dispatch (caller that passes the site).
- `python/review_pipeline.py` sentinel detection — confirm parity need during drafting.
- Tests: `python/test_research_eval.py`, `python/test_launch_review.py`, `python/test_agents.py`, `python/test_implement_dispatch.py`, and a collector-level assertion.

### Open questions
- Exact warning channel: validator stdout marker consumed by the collector vs collector-side detection.
- Whether `review_pipeline.py:1257` needs the same trailing-sentinel broadening for parity.
