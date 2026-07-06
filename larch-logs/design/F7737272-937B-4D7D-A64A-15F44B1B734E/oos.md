### FINDING_1: Testing strategy misstates accrual prerequisite
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The plan treats post-repair accrual as a single heatmap-run threshold, but the prerequisite is satisfied by either the calendar date or enough restored post-repair runs. That can wrongly block a valid demotion after the date threshold or invite implementers to treat per-row run counts as the only gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Split the gate in Testing strategy (and Edge cases): first assert accrual is satisfied (date >= 2026-07-17 OR design post-repair transcript coverage >= 50 runs), then separately assert each demotion target shows never-read heatmap evidence (reads_observed=0 with sufficient measured runs on that row).
  - From Cursor-Innovation: Add an implement-first gate: refuse demotion unless a fresh heatmap shows design reference_capture_status=measured and transcript_runs_observed>=50 (or the calendar prerequisite), and each demotion cites a post-repair row for that file


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: No post-merge halt-rate check for the issue acceptance criterion
- **Description**: No post-merge halt-rate check for the issue acceptance criterion. Scenario: The issue requires no orchestrator halt-rate regression across the next 20 runs after demotion; the plan verifies closure shrink only
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md
- **Phase**: design

Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

