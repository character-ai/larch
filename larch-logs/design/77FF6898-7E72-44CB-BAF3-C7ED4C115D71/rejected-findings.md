### [Plan Review] FINDING_3

### FINDING_3: NDJSON structured rows must use `category` field, not heading-based markdown aggregation per row body
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Reusing `parse_markdown_execution_issues` on each NDJSON row `body` re-buckets bullets by embedded `###` headings instead of the row's `category` field. That changes totals vs legacy fixtures, can return empty listing groups while counts are non-zero, and omits implement warnings/exec rows from the detail block that already appear in run-summary counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: For structured rows, treat `category` as the sole bucket: fence-aware bullet parse on `body` only, append events to exec or warn per `category`, then global dedupe. Add one NDJSON row test where `body` contains a foreign `###` heading and assert category field wins.
  - From Cursor-Pragmatic: For structured all-dict NDJSON, route each row by its `category` field and run fence-aware bullet parsing directly on `body` (plus the documented zero-bullet `max(1, …)` fallback). Reserve `parse_markdown_execution_issues` for concatenated legacy markdown that actually contains `### Tool Failures|External Reviewer Issues|Warnings` headings.


### [Plan Review] FINDING_4

### FINDING_4: Design final-summary must load exec/warning data after `_run_design_failure_report_gate`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Concern**: On `phase == "post"`, `_run_design_failure_report_gate` can append Warnings rows to `execution-issues.md` when the gate fails. Loading `load_result` before the gate and reusing it for both `invoke_render` and the detail block restores stale run-summary bullets (`- **Exec issues**` / `- **Warnings**`) and omits gate-appended rows from `## Exec Issues and Warnings`. Current code reloads counts after the gate (see `design_summary.py` lines 372–373).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Load `load_result` only after `_run_design_failure_report_gate`, then pass `count_load_result(load_result)` into `invoke_render` and reuse the same `load_result` for `build_issue_detail_section` (no pre-gate load)


### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/exec_issue_detail.py:91-108
- **Concern**: [SCOPE-REDUCTION] Haiku `subprocess.run(["claude", "--print", ...])` assessment adds a new LLM dependency, latency, token cost, and ~200 lines of prompt/parse/fallback code for every non-empty category. Scenario: The issue requires explicit listing of exec issues and warnings with descriptions; the example assessments are illustrative ("something like"). Listing redacted `display_text` rows alone satisfies the stated gap without blocking final-summary on Claude availability or adding per-run subprocess cost
- **Proposed resolution**: Ship v1 with `render_issue_detail_block(..., assess=False)` (numbered rows only). Add assessments later behind an env flag if operators still want them


