### [Plan Review] FINDING_1

### FINDING_1: Single outcome mapper must be shared and public
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The plan needs one shared outcome-display source of truth, but it currently allows either importing a private helper across modules or duplicating the mapping locally, which can either fail pyright private-usage checks or drift from the canonical display.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the shared mapper public before cross-module use, or revise the plan to use local constants or hardcoded `DONE` in those callers and remove the private-import option.
  - From Cursor-Innovation: Remove the local-equivalent option; require importing and using `_map_outcome_display` from `pr_body` (same as `final_report.py`)


### [Plan Review] FINDING_2

### FINDING_2: Degraded fallback Outcome display is not covered
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The degraded fallback that hand-writes the Outcome bullet is not covered by the proposed test updates, so a regression to raw approved/stalled would still pass the named design-summary test path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `### UPDATED: python/tests/design/test_design_summary.py` with an assertion that degraded `approved` output contains `- **Outcome**: DONE` (and optionally `stalled` → `STALLED` in a sibling case)
  - From Cursor-Pragmatic: Add ### UPDATED: python/tests/design/test_design_summary.py: assert - **Outcome**: DONE in test_render_final_summary_degraded_fallback_includes_issue_count_bullets for --outcome approved


### [Plan Review] FINDING_3

### FINDING_3: Degraded fallback warning still precedes Outcome
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: When the shared renderer fails, the degraded fallback still writes its warning before the mapped Outcome line, so the first body line on this named path is not the required status line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Move the mapped Outcome write immediately after the heading blank line, then write the degraded warning and the remaining bullets.


