## Proposed Design Outline

### Goals
- Cap reviewer-panel wall time so one or two stragglers cannot hold up a round; drop slots that exceed a quorum-anchored deadline.
- Make the cutoff opt-in per panel and env-tunable (multiple, floor, quorum); `multiple=0` restores today's wait-for-all.

### Non-goals
- No cutoff for non-reviewer waterfall panels (voting, decompose, aggregator); they keep wait-for-all.
- No fallback cascade for dropped stragglers; genuine-crash / empty-output fallback is unchanged.
- No change to the per-reviewer `--timeout` ceiling values.

### Approach sketch
- Add a quorum-anchored straggler deadline inside the shared reaper, engaged only when an opt-in flag is passed.
- Rewrite `_reap_phase` from per-launch blocking waits into one concurrent poll loop: once a quorum fraction of slots exit successfully, anchor on the quorum-th (slowest-of-quorum) elapsed, set `deadline = clamp(multiple * anchor, floor, ceiling)`, then SIGTERM remaining slots.
- Return straggler-dropped indexes so `_collect_phase` marks them dropped and never feeds them to the fallback queue.
- Pass the opt-in flag only from reviewer-panel callers; leave voters/decompose/aggregator untouched.

### Surfaces in scope
- `python/agent_waterfall.py` (reaper rewrite + opt-in flag + env readers; core change)
- `python/plan_review_panel.py`, `python/review_pipeline.py` (pass the opt-in flag)
- `python/test_agent_waterfall.py` (tests); `docs/configuration-and-permissions.md` (env-var docs)

### Open questions
- None.
