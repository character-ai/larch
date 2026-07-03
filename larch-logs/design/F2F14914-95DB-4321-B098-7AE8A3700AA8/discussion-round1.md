## Decision 1: Which observable symptom this fix must resolve
- **Question**: Is the bug about the committed `larch-logs/design/<RUN_ID>/final-summary.md` file being empty/missing, the live chat-visible summary not appearing, or both?
- **Resolution**: Operator did not respond to the clarifying question within the timeout. Proceeding on best judgment from confirmed evidence: all 20 most recent committed `/design` runs have an empty/missing `final-summary.md`, and this is directly explained by `step5c_core` committing the design-log publish PR before `_step5c_render_final_summary` writes real content. A direct isolated test of `render_final_summary_main` shows it renders correctly in isolation, so the live chat output (read from `$DESIGN_TMPDIR/final-summary.md` only after the whole Step 5c process — including the render call — completes) is not implicated by this same ordering defect. Primary acceptance criterion: the committed run-log file and the `larch:final-summary` tracking-issue comment must contain full enriched content, not be empty/stale, once a run publishes.
- **Source**: codebase investigation (operator non-responsive; re-raise if this turns out to be the wrong read)

## Decision 2: Scope — which call sites to fix
- **Question**: Should the fix cover every place `design log-publish` runs before the enriched final-summary render, or just the main Step 5c approved path?
- **Resolution**: Fix consistently everywhere the same "publish commits before render" ordering exists: `design_step5c.py` (both the approved/failed-plan-write path and the failed-publish-tail path), the clarify-publish flow (`clarify.py`), and the pause-save-publish flow (`design_pause.py`) — all three independently invoke `design log-publish` ahead of, or without coordinating with, a fully-rendered final-summary. A fix scoped to only Step 5c's happy path would leave the identical defect in the sibling flows.
- **Source**: codebase

## Decision 3: Non-goal — don't touch rendering content/internals
- **Question**: Does this fix need to change what `final-summary.md` contains (schema, cost/token calculations, plan-review provenance lines), or only when it gets written relative to the git publish?
- **Resolution**: Timing/ordering only. The issue title is "no longer outputting", not "outputting wrong content" — `render_final_summary_main`'s content logic is unaffected and tested independently; do not refactor it.
- **Source**: codebase
