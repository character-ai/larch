## Decision 1: Corrected-chart outcome (done criteria)
- **Question**: Should the fixed "Round N reviewer timing" Gantt shrink its window to reviewer/voter time, or keep the window and add a labeled bar for the Gate B apply/dedup/postplan span?
- **Resolution**: Add a labeled Gate B bar. Keep the round window spanning the full elapsed time; record a labeled bar/segment (e.g. `gate-b/apply`) covering the Gate-B apply + dedup + postplan-validation span so the currently-blank trailing gap is attributed. Do NOT shrink the window. Do NOT move the round-end (`end_s`) timestamp. Matches issue expected-behavior (b).
- **Source**: user (recommended option; non-response within 60s → accepted recommendation per terse-answer rule)

## Decision 2: Fix scope boundary
- **Question**: Does the fix apply only to `/design` plan-review round timing, or also to `/implement` / other Gantt charts?
- **Resolution**: Scoped to the `/design` plan-review round-timing Gantt only (the `### Round N reviewer timing` charts in `final-summary.md`). Do not touch `/implement` review timing or unrelated timing charts.
- **Source**: issue (explicitly scoped to `/design` plan-review)

## Decision 3: Hard constraint — preserve ledger + timestamp semantics
- **Question**: May the fix change the `v1 round` / `v1 vendor` timing-ledger row grammar or the round-end timestamp placement that other consumers rely on?
- **Resolution**: Preserve the existing `v1 round` and `v1 vendor` ledger row grammar and the round-end (`end_s`) timestamp semantics. The chosen fix adds a new labeled bar (new ledger row of an existing format) rather than moving the round-end stamp, so existing consumers of the round timestamp are unaffected. Verify no consumer breaks before adding any new row shape.
- **Source**: codebase / issue open-question 2

## Decision 4: Non-goal — do not hide the time
- **Question**: Is it acceptable to simply drop / silently fold away the Gate B time?
- **Resolution**: No. The user wants the time attributed (visible and labeled), not hidden. The blank tail must become a labeled span, not disappear.
- **Source**: issue expected-behavior
