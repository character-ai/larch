### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_summary.py:644-652
- **Concern**: Private outcome mapper is planned as a production cross-module import despite fatal private-usage checks. Scenario: The plan adds `_map_outcome_display` as module-private in `pr_body.py` but tells `design_summary.py` and optionally `final_report.py` to import or use it. Following that allowed path triggers `reportPrivateUsage=error` under `python/pyrightconfig.json` and blocks verification.
- **Proposed resolution**: Make the shared mapper public before cross-module use, or revise the plan to use local constants or hardcoded `DONE` in those callers and remove the private-import option.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/design/design_summary.py:644-652
- **Concern**: Plan allows a thin local Outcome mapper instead of importing the shared helper. Scenario: The degraded fallback is the only path that bypasses `render run-summary`; a duplicated mapper can drift from `pr_body._map_outcome_display`, so renderer failure can still emit raw `approved`/`stalled` while the normal path shows `DONE`/`STALLED`
- **Proposed resolution**: Remove the local-equivalent option; require importing and using `_map_outcome_display` from `pr_body` (same as `final_report.py`)

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/design/test_design_summary.py:481-516
- **Concern**: Degraded fallback Outcome display is not covered by the plan’s test deliverables. Scenario: `test_render_final_summary_degraded_fallback_includes_issue_count_bullets` exercises the only code path that hand-writes the Outcome bullet; without an assertion for `- **Outcome**: DONE`, a degraded-path regression would pass `pytest python/tests/design/test_design_summary.py` listed in the testing strategy
- **Proposed resolution**: Add `### UPDATED: python/tests/design/test_design_summary.py` with an assertion that degraded `approved` output contains `- **Outcome**: DONE` (and optionally `stalled` → `STALLED` in a sibling case)

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/design/design_summary.py:644-652
- **Concern**: Degraded fallback still puts warning before Outcome. Scenario: When the shared renderer fails, the /design fallback writes the degraded warning before the Outcome line, so the first body line still is not the required status line on this named final-report path.
- **Proposed resolution**: Move the mapped Outcome write immediately after the heading blank line, then write the degraded warning and the remaining bullets.

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/git/pr_body.py:554-558
- **Concern**: Plan adds unconditional Outcome but never says to delete the existing conditional Outcome block. Scenario: An implementer can leave the outcome.startswith(...) append and also add the mapped unconditional line, producing duplicate Outcome bullets on bailed/stalled/cancelled/failed paths with conflicting raw vs display values
- **Proposed resolution**: In the pr_body.py step, remove the conditional Outcome block entirely and keep one unconditional first bullet: - **Outcome**: {_map_outcome_display(outcome)}

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/design/test_design_summary.py:481-516
- **Concern**: Degraded /design fallback has no Outcome display test despite being a named fix surface. Scenario: test_render_final_summary_degraded_fallback_includes_issue_count_bullets still passes if the degraded writer regresses to raw approved after design_summary.py is fixed
- **Proposed resolution**: Add ### UPDATED: python/tests/design/test_design_summary.py: assert - **Outcome**: DONE in test_render_final_summary_degraded_fallback_includes_issue_count_bullets for --outcome approved

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/report/test_run_logs.py:1015-1028
- **Concern**: Flush pre-recovery test still pins live-render stall output to lowercase `stalled`. Scenario: The plan’s `test_run_logs.py` updates focus on legacy reconciliation fixtures, but `test_flush_logs_pre_rewrites_stalled_summary_after_clean_pr_recovery` renders a fresh stalled summary via `flush_logs_pre`; after `_map_outcome_display`, line 1015 will fail because the bullet becomes `- **Outcome**: STALLED`
- **Proposed resolution**: Add an explicit plan step for this test: stall phase expects `- **Outcome**: STALLED`; recovery phase expects `- **Outcome**: DONE` (not only absence of lowercase `stalled`)

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/report/test_run_logs.py:1028
- **Concern**: Recovery assertion only rejects lowercase `stalled` in the Outcome bullet. Scenario: After mapping, a failed re-render that leaves `- **Outcome**: STALLED` would still satisfy line 1028, so the always-present success contract can regress undetected
- **Proposed resolution**: In the same flush test, assert `- **Outcome**: DONE` after recovery and reject both `stalled` and `STALLED` residue in the Outcome bullet
