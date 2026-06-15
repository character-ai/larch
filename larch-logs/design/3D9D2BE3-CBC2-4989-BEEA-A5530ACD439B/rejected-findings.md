### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/progress_report.py:134-149
- **Concern**: _is_ci_gantt_row omits shell base()/tolower normalization. Scenario: Plan says mirror scripts/render-review-phase-detail.sh but only lists basename predicates. Shell applies base(path) and tolower(kind/out). Ledger/tests can store full output paths (python/test_progress_report.py _write_vendor_timing). Kind/output checks on raw columns miss CI/probe rows or drift from committed Gantt filtering.
- **Proposed resolution**: In _is_ci_gantt_row, lower kind; derive bn = Path(output).name.lower() when output else ""; run basename predicates on bn. Add mixed-row test with a full-path CI output.

