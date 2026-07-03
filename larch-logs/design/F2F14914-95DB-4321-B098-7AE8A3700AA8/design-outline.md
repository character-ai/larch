## Proposed Design Outline

### Goals
- The committed `larch-logs/design/<RUN_ID>/final-summary.md` and the `larch:final-summary` tracking-issue comment must carry the full enriched summary after a `/design` run publishes, not an empty/stale snapshot.
- Fix the same "log-publish commits before the enriched render" ordering defect consistently everywhere it occurs, not only on the primary happy path.

### Non-goals
- No change to what `render_final_summary_main` computes or renders (cost, tokens, plan-review line, difficulty, etc.).
- No change to the live chat-visible summary emission mechanism (the orchestrator Read-after-notification path) — not confirmed broken, and out of scope unless new evidence emerges during implementation.
- No broader refactor of Step 5c, clarify, or pause-save control flow beyond correcting this ordering.

### Approach sketch
- In each affected flow, ensure the enriched final-summary render completes and is reflected in `$DESIGN_TMPDIR` before the `design log-publish` git commit captures that tree, while preserving any content that legitimately depends on the publish outcome (PR number/URL, rename state).
- Primary surface: `python/larch/design/design_step5c.py` (`step5c_core`) — both the approved/failed-plan-write branch and the failed-publish-tail branch currently render after invoking the publish tail.
- Secondary surfaces: `python/larch/design/clarify.py` (clarify-publish flow) and `python/larch/design/design_pause.py` (pause-save publish) — both independently call `design log-publish` and need the same ordering check.
- Exact mechanism (reorder vs. render-twice-and-refresh vs. other) decided per file during plan drafting, grounded in each file's actual control flow.

### Surfaces in scope
- python/larch/design/design_step5c.py
- python/larch/design/clarify.py
- python/larch/design/design_pause.py
- Associated test files covering these modules

### Open questions
- None.
