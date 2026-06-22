### FINDING_1: Plan cites nonexistent test name for step 2b postplan pause
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan inventory references `test_step2b_postplan_pause_requested_exits_11`, but the real direct `_shared_step2b_postplan_body` test is `test_step2b_postplan_rc_11_raises_system_exit`. Implementers may skip work or duplicate tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Rename the plan inventory to test_step2b_postplan_rc_11_raises_system_exit and require passing an explicit resolved design_tmpdir Path (not ambient DESIGN_TMPDIR alone)


### FINDING_5: validator_autofix_main builds ctx before DESIGN_TMPDIR validate/resolve
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `validator_autofix_main` builds `ctx` immediately after `_rehydrate_validator_env`, before `validate_design_tmpdir` and `Path(...).resolve()` normalize `DESIGN_TMPDIR`. `ctx.design_tmpdir` can keep a pre-resolve or invalid tmpdir while later logic and `_validator_pause_save` use the resolved path; symlink or validation fixes diverge from the snapshot, breaking parity with the step5c normalized-wins contract and the planned symlink regression intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Mirror the step5c_core anchor: rehydrate, validate/resolve DESIGN_TMPDIR into os.environ and normalized_overrides, then build ctx once, then run pause/operator-cancel paths with that ctx.
  - From Cursor-Requirements: Mirror `step5c_core`: validate and resolve `design_tmpdir`, apply `normalized_overrides` with the resolved value, then build `ctx` once immediately before the first helper that reads via `ctx` (including `_validator_pause_save`)


### FINDING_6: degraded_tools_gate_main ctx merge must include parsed CLI flag values
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `degraded_tools_gate_main` ctx merge must include parsed CLI flag values. Parser defaults are bound from ambient `os.environ` at definition time; presence/binary flags arrive via `--codex-present`, `--cursor-present`, etc. Building `ctx` from `os.environ` alone (without `vars(args)` overrides) can ignore explicit argv and diverge from `degraded_tools_result` inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: After argparse, merge vars(args) presence/binary-found fields into the ctx mapping before Ctx.from_mapping; route converted reads from that snapshot, not a pre-parse environ copy.


### FINDING_7: render_final_summary_main needs argv-first precedence for new CLI args
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `render_final_summary_main` needs argv-first precedence for new CLI args. The plan adds `--design-tmpdir`/`--issue-number`/`--session-id` for converted cores, but `render_final_summary_main` currently always reads `DESIGN_TMPDIR`, `SESSION_ID`, and `ISSUE_NUMBER` from `os.environ`. If env is stale while explicit args are passed (the IPC-removal goal), render/token refresh can target the wrong tmpdir or issue metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Parse the new flags and apply argv-wins precedence (same pattern as plan_quality argv-first mains): use explicit args when provided, env fallback only for legacy callers.
```

**Merge notes**

| Source IDs | Action |
|---|---|
| FINDING_8 + FINDING_11 | Same behavioral risk (`validator_autofix_main` ctx before resolve); merged as FINDING_5 |
| FINDING_3, 4, 5, 6, 9, 10 | Distinct code paths or fixes; kept separate |


### FINDING_8:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/plan_quality.py:999-1243
- **Concern**: [SCOPE-REDUCTION] Grouping `validate_plan_main` / `check_plan_size_main` with `validator_autofix_main` under one `{**os.environ, **rehydrate_merged, **argv_overrides}` recipe is ambiguous. Scenario: Only `validator_autofix_main` calls `_rehydrate_validator_env` today; the other two are direct CLI/harness entrypoints with no wrapper session file. Applying validator rehydrate (or the wrong allowlist defaults) to `validate_plan_main` / `check_plan_size_main` would change `DESIGN_TMPDIR`, `SITE`, and validator-status precedence on standalone `plan validate` / `plan check-size` calls
- **Proposed resolution**: Split the plan: `validator_autofix_main` keeps `_rehydrate_validator_env` then ctx merge; `validate_plan_main` and `check_plan_size_main` build ctx from `{**os.environ, **argv_overrides}` only (no validator rehydrate)


