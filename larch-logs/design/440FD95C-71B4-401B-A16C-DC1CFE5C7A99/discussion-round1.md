## Decision 1: Fix scope for this bundled follow-up
- **Question**: Which parts of this bundled follow-up should the plan fix?
- **Resolution**: Fix everything: the stale-tracking-comment risk, the 4 test-coverage gaps, and extend centralized rendering to cancellation/failed-publish-tail paths in design_terminal.py.
- **Source**: user

## Decision 2: Commit behavior for cancellation/failed-publish-tail paths
- **Question**: Should cancellation and failed-publish-tail outcomes start committing an enriched summary to larch-logs, or should the fix stay local (no new commits)?
- **Resolution**: Also commit to larch-logs. These paths must call the full `design log-publish` flow, so every such run opens a larch-logs commit and PR. Codebase check: "paused" outcomes already redirect to `pause_save_main`'s own correct centralized-render-and-publish call (`design_pause.py`), so they are excluded from this gap and need no change. Apply the fix uniformly to the other outcomes `step_final_summary_core` handles (the `cancelled-*` and `failed-*` outcomes it renders), since that is the simplest, most consistent approach.
- **Source**: user + codebase

## Decision 3: Failure-signal contract for the tracking-comment upsert
- **Question**: If the tracking-comment upsert fails after clarify reuses the rendered body, should that flip CLARIFY_PUBLISH_STATUS/PUBLISH_OK, or only get logged?
- **Resolution**: Flip status on failure. A failed tracking-comment upsert must flip PUBLISH_OK/CLARIFY_PUBLISH_STATUS to false so downstream consumers (SKILL.md control flow, tests) see the failure.
- **Source**: user
