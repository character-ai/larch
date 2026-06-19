## Proposed Design Outline

### Goals
- Cap reviewer-round wall time so one or two stragglers cannot hold up `/design`, `/implement`, and `/review` reviewer panels.
- Anchor the cap on the round's own pace (half-mark median), not a fixed timeout.
- Drop timed-out stragglers cleanly: no fallback cascade, no false panel-failure.

### Non-goals
- No change to voters, the findings aggregator, or the decompose panel; they keep wait-for-all.
- No change to the per-reviewer `--timeout` ceiling.
- No change to fallback for genuine crashes or empty outputs.

### Approach sketch
- Rewrite `_reap_phase` in `python/agent_waterfall.py` into one concurrent poll loop with an adaptive deadline; return straggler-dropped indexes.
- Anchor = slowest of the first ceil(N/2) substantive successes (rc==0 + non-empty); `deadline = clamp(2.5 x anchor, 300s floor, --timeout ceiling)`.
- Gate the cutoff behind a new opt-in flag passed only by the reviewer dispatch sites; voters/aggregator/decompose omit it.
- Tag straggler drops distinctly so `check_reviewer_failure_threshold` ignores them; disable fallback by keeping them out of `failed`.

### Surfaces in scope
- `python/agent_waterfall.py` (core), `python/review_pipeline.py` (opt-in + threshold gate), `python/plan_review_panel.py` (opt-in).
- `python/test_agent_waterfall.py` (tests), `docs/configuration-and-permissions.md` (env knobs).

### Open questions
- None.
