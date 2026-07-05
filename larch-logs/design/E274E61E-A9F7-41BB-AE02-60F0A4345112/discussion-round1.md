## Decision 1: Mode: line removal scope
- **Question**: The issue says "In /implement, Mode: first line is invalid and should be dropped." Design already suppresses Mode:. Does the removal affect any other path?
- **Resolution**: Only implement's final report shows Mode:; design already has `if skill != "design"` guard. Change is limited to removing that Mode: emit for implement in `render_run_summary`.
- **Source**: codebase (pr_body.py:558)

## Decision 2: Outcome: always-present scope
- **Question**: The issue title says "in /design and /implement". Should Outcome: always be emitted for both skills?
- **Resolution**: Yes. Both design and implement share `render_run_summary`. Always emit Outcome: with mapped display value for both skills.
- **Source**: codebase (pr_body.py:554-556)

## Decision 3: Outcome display value mapping
- **Question**: Which outcomes map to DONE vs STALLED vs raw value?
- **Resolution**: DONE for all "success" outcomes (merged, force-merged-externally, pr-created, pr-created-draft, design-only, forked-dry-run for implement; approved, approved-partition for design). STALLED for stalled. All other outcomes (bailed, bailed-needs-user-input, cancelled-*, failed-*, publish-skipped, paused) keep their raw value.
- **Source**: codebase (write-final-report.md outcome enum + design _VALID_OUTCOMES)

## Decision 4: Reconciliation backward compat
- **Question**: `_summary_stalled_outcome_index` regex looks for lowercase `stalled`. After the change it's STALLED. Does reconciliation need updating?
- **Resolution**: Yes. Update the regex to case-insensitively match both `stalled` and `STALLED` so old stored summaries can still be reconciled.
- **Source**: codebase (final_report.py:533-537, tests/report/test_run_logs.py:1048)
