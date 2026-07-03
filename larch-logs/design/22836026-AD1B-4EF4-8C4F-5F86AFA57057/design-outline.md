## Proposed Design Outline

### Goals
- Attribute the unlabeled trailing gap in `/design` "Round N reviewer timing" Gantt charts to a visible, labeled Gate B span.
- Keep the round window and round-end (`end_s`) timestamp unchanged, so no other consumer of that timestamp is affected.

### Non-goals
- Do not shrink the round window or move the round-end stamp.
- Do not touch `/implement` review timing or unrelated Gantt charts.
- Do not break the `v1 round` / `v1 vendor` timing-ledger grammar.

### Approach sketch
- Emit one labeled bar (e.g. `gate-b/apply`) as a `v1 vendor`-style ledger row spanning the Gate B apply + dedup + postplan work.
- Bar start = when reviewers/voters finished (tally done); bar end = round-end stamp. Both are knowable at the `awaiting-continuation` round-finalize.
- Emit only on the accepted-findings path (`plan_review.py:479`, Gate B ran); the zero-findings path (`:423`) has no gap, so no bar.
- Confirm the existing Gantt renderer draws the new row inside the round window with no layout change.

### Surfaces in scope
- `python/larch/review/plan_review.py` — `awaiting-continuation` round-finalize call site.
- `python/larch/review/plan_review_loop.py` — round-timing stamp helper (span-start source).
- `python/larch/report/timing.py` — `record_vendor_task` ledger row (bar emit).
- `python/larch/report/progress_report.py` — verify render; change only if needed.
- Tests under `python/larch/**` covering timing and plan-review.

### Open questions
- Span-start source: reuse the max voter/reviewer bar end vs. stamp a dedicated "reviewers-done" timestamp at tally.
