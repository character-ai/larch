### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/exec_issue_detail.py:106-107
- **Concern**: Assessment parser must unwrap Claude `--output-format json` envelope before schema validation. Scenario: `claude --print --output-format json` returns a wrapper object whose `result` field is a string (see `agents.py` launch-claude-subprocess). Parsing stdout as `{"assessments":[...]}` directly always fails schema validation, so every run renders rows with no assessment lines despite a working `claude` binary.
- **Proposed resolution**: Match existing subprocess handling: `json.loads(stdout)`, reject when `is_error`, read string `result`, `json.loads` that inner text, then validate `assessments`. Add a mocked test with envelope-shaped stdout, not bare assessments JSON.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/exec_issue_detail.py:105
- **Concern**: Haiku model default is unspecified when `LARCH_EXEC_ISSUE_ASSESSMENT_MODEL` is unset. Scenario: The plan only binds `--model` from env when set. Implementations that always pass `--model` without a fallback fail closed (no assessments); implementations that omit `--model` inherit an operator-specific default and get non-deterministic behavior.
- **Proposed resolution**: Pin a documented default Haiku slug (same style as other larch model defaults) and allow env override. Test both env-set and env-unset paths.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/exec_issue_detail.py:72-75
- **Concern**: Structured NDJSON rows must not run full `###` section splitting on each `body`. Scenario: Current `_refresh_issue_counts` assigns bullets using the row `category` plus fence-aware `- ` counting on the whole `body`, ignoring embedded `###` headings. The plan says "parse `body` through markdown bullet rules scoped to that category" but does not forbid reusing `parse_markdown_execution_issues` per row. That walker would re-bucket bullets by in-body headings and can change totals and listed rows vs legacy fixtures.
- **Proposed resolution**: For structured rows, treat `category` as the sole bucket: fence-aware bullet parse on `body` only, append events to exec or warn per `category`, then global dedupe. Add one NDJSON row test where `body` contains a foreign `###` heading and assert category field wins.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/design_summary.py:372-380
- **Concern**: Design final-summary loads exec/warning data before `_run_design_failure_report_gate` and reuses that `LoadResult` for both `invoke_render` and the detail block; the plan claims tmpdir issue files are stable across that window. Scenario: On `phase == "post"`, `_run_design_failure_report_gate` can append to `execution-issues.md` when the gate fails (`run-log append-failure`, category Warnings). Today line 373 reloads counts after the gate. Moving load before the gate restores stale run-summary bullets (`- **Exec issues**` / `- **Warnings**`) and omits gate-appended rows from `## Exec Issues and Warnings`
- **Proposed resolution**: Load `load_result` only after `_run_design_failure_report_gate`, then pass `count_load_result(load_result)` into `invoke_render` and reuse the same `load_result` for `build_issue_detail_section` (no pre-gate load)



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/exec_issue_detail.py:91-108
- **Concern**: [SCOPE-REDUCTION] Haiku `subprocess.run(["claude", "--print", ...])` assessment adds a new LLM dependency, latency, token cost, and ~200 lines of prompt/parse/fallback code for every non-empty category. Scenario: The issue requires explicit listing of exec issues and warnings with descriptions; the example assessments are illustrative ("something like"). Listing redacted `display_text` rows alone satisfies the stated gap without blocking final-summary on Claude availability or adding per-run subprocess cost
- **Proposed resolution**: Ship v1 with `render_issue_detail_block(..., assess=False)` (numbered rows only). Add assessments later behind an env flag if operators still want them



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/exec_issue_detail.py:72-75
- **Concern**: NDJSON structured rows must not use heading-based markdown aggregation on bare row bodies. Scenario: Implement NDJSON fallback counts bullets in each row body via fence-aware `- ` scanning without `###` headings (`test_refresh_issue_counts_counts_structured_rows_per_bullet`). If `_parse_ndjson_structured_rows` delegates to `parse_markdown_execution_issues(body)` on bodies like `- a\n- b\n`, listing returns empty groups while totals should be non-zero, so `count_load_result` regresses and the detail block omits implement warnings/exec rows that already appear in the run-summary counts.
- **Proposed resolution**: For structured all-dict NDJSON, route each row by its `category` field and run fence-aware bullet parsing directly on `body` (plus the documented zero-bullet `max(1, …)` fallback). Reserve `parse_markdown_execution_issues` for concatenated legacy markdown that actually contains `### Tool Failures|External Reviewer Issues|Warnings` headings.



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/exec_issue_detail.py:91-108
- **Concern**: Assessment helper lacks a pinned default model when `LARCH_EXEC_ISSUE_ASSESSMENT_MODEL` is unset. Scenario: The issue asks for per-item materiality lines. The plan only names a model when the env var is set; other `claude --print` call sites always pass an explicit `--model`. If implementers omit `--model` when unset, subprocess fails, `assess_issue_details` returns `{}`, and finals ship row text only with no assessments in the common path.
- **Proposed resolution**: Pin a default Haiku slug when the env var is unset (same pattern as `agents.py` / `design_lifecycle.py` model defaults) and test one mocked-success assessment path with no env override.



### FINDING_8:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/exec_issue_detail.py (planned assess_issue_details)
- **Concern**: Assessment JSON parsing targets the wrong Claude output shape. Scenario: The plan invokes claude --print --output-format json but then requires stdout to be the model payload with a top-level assessments array. Existing Claude subprocess callers parse an envelope and extract the result string first, so successful assessment calls would be treated as schema mismatches and every final summary would omit the requested materiality lines.
- **Proposed resolution**: Parse the Claude JSON envelope first, validate result is a string, JSON-decode that string as the assessments payload, and add a test using the envelope shape from the existing Claude subprocess contract. Alternatively drop --output-format json and parse direct text output.



