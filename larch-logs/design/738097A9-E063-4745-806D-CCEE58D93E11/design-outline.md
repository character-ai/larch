## Proposed Design Outline

### Goals
- Fix the in-flight reviewer-timing Gantt so round N>1 shows only the current round's rows (no prior-round leak), for BOTH /implement Step 5 and /design plan-review.
- Persist `round-start-s` at round START on every normal path so the in-flight window is correct from the moment a round begins.
- Add regression coverage that fails on today's bug: normal-path round-start-s write (both skills) + in-flight no-prior-round-leak.

### Non-goals
- No timing-ledger schema change (no round column added).
- No basename / panel-manifest attribution filter (verified ineffective: basenames repeat every round, ledger has no round column).
- No rework of per-round chart content or styling (that was #4543, already merged).

### Approach sketch
- `review_and_fix.py`: call `_persist_round_start(...)` immediately after `start_s` is captured at round start, before `_run_round`, on every path (keep the idempotent escalation-branch call).
- `plan_review.py`: persist `round-start-s` at the /design plan-review round start (parity).
- `progress_report.py`: harden `_render_inflight_gantt` — when `round-start-s` is absent, derive the window start from the prior round's end, never from the whole-phase `window_start_s`.
- `render-review-phase-detail.sh`: audit settled per-round (type=round) charts for the same leak; harden if it leaks, else add a regression assertion.

### Surfaces in scope
- `python/review_and_fix.py`, `python/plan_review.py`, `python/progress_report.py`, `scripts/render-review-phase-detail.sh`
- Tests: `python/test_review_and_fix.py`, `python/test_plan_review.py`, `python/test_progress_report.py`, settled-chart harness (`scripts/test-render-review-phase-detail.sh` or sibling)

### Open questions
- Fallback lower-bound when round-start-s is missing: leaning to "prior round's end" (robust, includes the current round's pre-reviewer setup span). Will confirm against the settled-chart audit during drafting.
