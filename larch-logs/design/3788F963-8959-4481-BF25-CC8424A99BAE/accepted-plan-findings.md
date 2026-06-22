### FINDING_1: Cursor CI normative table omits promote, failure append, and emit
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The Cursor CI normative epilogue table stops after the stall guard (steps 1–5) and omits `_promote_inner_done`, `_append_ci_failure`, and `_emit_ci_launcher_result`, even though `launch_cursor_ci_main` runs them after stall (~3713–3715) and the Codex CI table documents the full eight-step tail. A hook list built only from the truncated table can skip promote/failure/emit, breaking `.done` IPC and CI launcher-result stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add steps 6-8 to the Cursor CI table: `_promote_inner_done` → `_append_ci_failure` → `_emit_ci_launcher_result`, matching current `launch_cursor_ci_main` (~3713-3715) and the Codex CI table format
  - From Cursor-Innovation: Extend the Cursor CI table with explicit steps 6-8: `_promote_inner_done`, `_append_ci_failure`, `_emit_ci_launcher_result`, matching Codex CI steps 6-8 and current code order.
  - From Cursor-Requirements: Add steps 6-8 to the Cursor CI normative table: `_promote_inner_done`, `_append_ci_failure`, `_emit_ci_launcher_result`, matching the Codex CI tail pattern


### FINDING_2: Codex implement normative table omits `_promote_inner_done`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The Codex implement normative epilogue table jumps from step 5 (failure append) to step 7 (emit) without an explicit `_promote_inner_done` step, while `launch_codex_implement_main` promotes between failure and emit (~5120–5121). Hook lists derived from the incomplete table can skip promote, leaving `.inner.done` unpromoted and breaking `collect_results` wait-on-`.done` IPC.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Insert step 6 `_promote_inner_done(output)` between failure append and `_emit_implement_launcher_envelope`; keep the adoption-scope 7-step list aligned with the numbered table
  - From Cursor-Innovation: Add step 6 `_promote_inner_done` explicitly; keep failure-before-promote and promote-before-emit ordering already stated at lines 151 and 285.
  - From Cursor-Pragmatic: Add step 6 _promote_inner_done between failure append and _emit_implement_launcher_envelope in the Codex implement normative table and mirror it in the launch_codex_implement_main hook list
  - From Cursor-Requirements: Add step 6 `_promote_inner_done` to the Codex implement normative table between conditional failure append and emit


### FINDING_3: Cursor implement normative table omits `_record_implement_timing`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The Cursor implement normative epilogue table omits `_record_implement_timing` and skips step numbering (meta as step 1, usage as step 3), while `launch_cursor_implement_main` records timing at ~5222–5224 between meta append and usage. A hook list built from this table can drop vendor timing entirely and desync vendor-task records.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add step 2 `_record_implement_timing("cursor", task_kind, start, output, result.exit_code)` and renumber the remaining steps to match `python/agents.py:5222-5228` and the test fixture at plan.txt:210
  - From Cursor-Innovation: Insert `_record_implement_timing` as step 2 between meta append and `_record_cursor_implement_usage`, matching ~5222-5224 and the acceptance bullet at line 285.
  - From Cursor-Pragmatic: Insert step 2 _record_implement_timing between Append .meta and _record_cursor_implement_usage in the Cursor implement normative table and hook list
  - From Cursor-Requirements: Add step 2 `_record_implement_timing` to the Cursor implement normative table; keep the documented order meta → timing → usage → failure → promote → emit


### FINDING_5: `run_external_agent` stale cleanup contract drops optional stdout/stderr paths
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: The plan migrates stale cleanup to `LauncherPaths` fields plus `output` only, but current `run_external_agent` also unlinks caller-supplied `stdout_path` and `stderr_path` (events.jsonl and sidecar for Codex CI) on retry. Omitting them leaves stale partial artifacts across auth retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: State explicitly that stale cleanup still adds Path(stdout_path) and Path(stderr_path) when those kwargs are set in addition to LauncherPaths fields; extend the run_external_agent migration test to cover both kwargs


