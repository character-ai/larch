### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_plan_review_panel.py:375-377
- **Concern**: `test_panel_dispatch_dynamic_scout_rows` still expects 12 manifest lines, but the planned generic static Codex row makes the round-1 dynamic panel emit 13.. Scenario: The test will fail as soon as the planned row is added, so the PR cannot go green.
- **Proposed resolution**: Bump the expected count to 13 in this test, alongside the other round-1 manifest count updates.

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_plan_review_panel.py:377
- **Concern**: Plan points 12→13 manifest bump at test_panel_dispatch_dynamic_rows_render_full_scaffold but the hard-coded count lives in test_panel_dispatch_dynamic_scout_rows. Scenario: Prior round accepted stale-count coverage, yet the plan still names render_full_scaffold (no len==12 assert at python/test_plan_review_panel.py:434-443). Only test_panel_dispatch_dynamic_scout_rows asserts == 12 at line 377. Following the plan literally updates the wrong test and py-test still fails on scout_rows.
- **Proposed resolution**: In ### UPDATED: python/test_plan_review_panel.py, change the 12→13 bullet to test_panel_dispatch_dynamic_scout_rows (line 377). Mirror the fix in Failure modes line 200. Optionally add the same count assert to render_full_scaffold only if you want both tests pinned.
