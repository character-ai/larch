### FINDING_1: Single outcome mapper must be shared and public
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The plan needs one shared outcome-display source of truth, but it currently allows either importing a private helper across modules or duplicating the mapping locally, which can either fail pyright private-usage checks or drift from the canonical display.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the shared mapper public before cross-module use, or revise the plan to use local constants or hardcoded `DONE` in those callers and remove the private-import option.
  - From Cursor-Innovation: Remove the local-equivalent option; require importing and using `_map_outcome_display` from `pr_body` (same as `final_report.py`)

### FINDING_2: Degraded fallback Outcome display is not covered
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The degraded fallback that hand-writes the Outcome bullet is not covered by the proposed test updates, so a regression to raw approved/stalled would still pass the named design-summary test path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `### UPDATED: python/tests/design/test_design_summary.py` with an assertion that degraded `approved` output contains `- **Outcome**: DONE` (and optionally `stalled` → `STALLED` in a sibling case)
  - From Cursor-Pragmatic: Add ### UPDATED: python/tests/design/test_design_summary.py: assert - **Outcome**: DONE in test_render_final_summary_degraded_fallback_includes_issue_count_bullets for --outcome approved

### FINDING_3: Degraded fallback warning still precedes Outcome
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: When the shared renderer fails, the degraded fallback still writes its warning before the mapped Outcome line, so the first body line on this named path is not the required status line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Move the mapped Outcome write immediately after the heading blank line, then write the degraded warning and the remaining bullets.

### FINDING_4: Conditional Outcome append can duplicate the new bullet
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The plan adds an unconditional Outcome bullet but never removes the existing conditional Outcome append, so several non-success paths can emit duplicate or conflicting Outcome bullets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In the pr_body.py step, remove the conditional Outcome block entirely and keep one unconditional first bullet: - **Outcome**: {_map_outcome_display(outcome)}

### FINDING_5: Flush test still only guards lowercase stalled
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The flush pre-recovery test still asserts against lowercase stalled only, so it can miss cases where the rendered outcome bullet becomes STALLED or fails to become DONE after recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add an explicit plan step for this test: stall phase expects `- **Outcome**: STALLED`; recovery phase expects `- **Outcome**: DONE` (not only absence of lowercase `stalled`)
  - From Cursor-Requirements: In the same flush test, assert `- **Outcome**: DONE` after recovery and reject both `stalled` and `STALLED` residue in the Outcome bullet
