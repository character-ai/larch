### FINDING_1: Stale manifest line count in `test_panel_dispatch_dynamic_scout_rows`
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: `test_panel_dispatch_dynamic_scout_rows` still asserts 12 non-empty manifest lines at `python/test_plan_review_panel.py:377`. Adding the planned generic static Codex row for rounds 1–2 makes round-1 dynamic panel dispatch emit 13 lines. The test fails as soon as that row lands, blocking a green `py-test` run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Bump the expected count to 13 in this test, alongside the other round-1 manifest count updates.

### FINDING_2: Plan cites wrong test for the 12→13 manifest bump
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan’s 12→13 manifest bump points at `test_panel_dispatch_dynamic_rows_render_full_scaffold`, but the hard-coded `== 12` assertion lives only in `test_panel_dispatch_dynamic_scout_rows` at line 377. `render_full_scaffold` (lines 434–443) checks rendered prompt scaffold content, not manifest length. Following the plan literally updates the wrong test; `scout_rows` still fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In ### UPDATED: python/test_plan_review_panel.py, change the 12→13 bullet to test_panel_dispatch_dynamic_scout_rows (line 377). Mirror the fix in Failure modes line 200. Optionally add the same count assert to render_full_scaffold only if you want both tests pinned.
