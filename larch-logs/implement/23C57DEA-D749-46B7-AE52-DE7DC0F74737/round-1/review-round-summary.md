# Review Round 1

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_6: `_tmpdir_guard_restore` follows symlinks and lets cleanup exceptions escape
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_tmpdir_guard_restore` follows symlinks and lets cleanup exceptions escape. A write-enabled auto-fix vendor creates a symlink to a directory under `DESIGN_TMPDIR`; restore raises during `shutil.rmtree` and `auto_fix_plan_commands_main` aborts before marking the attempt failed and restoring through the normal recovery path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Use lstat/is_symlink before is_dir, unlink symlinks without following them, and catch OSError so unsafe mutations return False.


### FINDING_7: Missing progress regressions for round-window aggregation and bad ledger
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required progress regressions for round-window aggregation and missing/malformed ledger are absent. `_progress_round_windows()` can regress while shell tests still pass; live progress reports show wrong windows or drop charts while breaking detail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add pytest fixtures for multi-row round aggregation and missing/all-bad ledger with assertions on title span and chart presence.


### FINDING_8: `sort | head` under pipefail truncates valid Gantt rows
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `sort | head` runs under pipefail and the fallback truncates valid extracted Gantt rows. Large timing ledgers can make `head` close the pipe after 25 rows, `sort` exits 141, and the report says no reviewer timing tasks despite overlapping rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Write sorted rows to a temp file before applying head, or handle the expected cap path without treating SIGPIPE as extraction failure


