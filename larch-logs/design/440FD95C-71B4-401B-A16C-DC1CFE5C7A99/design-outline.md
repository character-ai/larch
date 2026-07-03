## Proposed Design Outline

### Goals
- Fix clarify's stale-comment risk: reuse the already-rendered body, don't re-render.
- Surface tracking-comment upsert failures: flip `PUBLISH_OK`/`CLARIFY_PUBLISH_STATUS` instead of discarding them.
- Extend the centralized pre-copy render to cancellation and `failed-publish-tail` paths, so those outcomes commit an enriched summary to `larch-logs` too.
- Close the 4 test-coverage gaps the issue lists.

### Non-goals
- No change to "paused" handling; it already redirects to the correct publish call.
- No change to the shared `resolve_summary_mode` helper from #6151.
- No new CLI subcommands; reuse `design log-publish` and `render-final-summary`.

### Approach sketch
- `clarify.py`: read the body `design log-publish` already rendered, upsert the tracking comment directly, and check the result.
- `design_terminal.py`'s `step_final_summary_core`: call `design log-publish` for the outcomes it renders (all but "paused"), instead of a local, uncommitted render.
- Add or extend tests for the 4 coverage gaps named in the issue.

### Surfaces in scope
- `python/larch/design/clarify.py`, `design_terminal.py`, `design_log_publish_flow.py`
- Matching test files under `python/tests/design/`

### Open questions
- None.
