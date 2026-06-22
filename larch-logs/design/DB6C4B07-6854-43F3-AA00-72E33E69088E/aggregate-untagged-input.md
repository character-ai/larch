### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_design_lifecycle.py:1486-1495
- **Concern**: Plan cites missing test name test_step2b_postplan_pause_requested_exits_11. Scenario: The real direct _shared_step2b_postplan_body test is test_step2b_postplan_rc_11_raises_system_exit; implementers may skip or duplicate work
- **Proposed resolution**: Rename the plan inventory to test_step2b_postplan_rc_11_raises_system_exit and require passing an explicit resolved design_tmpdir Path (not ambient DESIGN_TMPDIR alone)

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/design_lifecycle.py:3136-3427
- **Concern**: Step 2b caller table says pass ctx after normalization but no ctx owner is defined. Scenario: Postplan/drafter may build duplicate snapshots or thread a half-built ctx while only Path threading is required this PR
- **Proposed resolution**: State explicitly that step2b_postplan_main and step2b_drafter_main pass ctx=None and only thread the entry-validated design_tmpdir Path into _shared_step2b_postplan_body; reserve Ctx builds to step5c_core and step_final_summary_core

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:3782-3783
- **Concern**: Failed-publish-tail render path omits explicit final_summary_path in the call-site inventory. Scenario: That branch calls _step5c_render_final_summary(design_tmpdir, env, failed-publish-tail) with no path arg today; removing FINAL_SUMMARY_PATH env IPC without a parameter breaks emit/delete when result_env is absent
- **Proposed resolution**: Add the failed-publish-tail branch to the final_summary_path inventory and require str(design_tmpdir / final-summary.md) at both _step5c_render_final_summary and _emit_final_summary_marked_from_disk call sites

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/design_lifecycle.py:1374-1393
- **Concern**: step_final_summary_main keeps pre-core rehydrate/validate while core rehydrates again. Scenario: Main and core can disagree on normalized DESIGN_TMPDIR if only core builds ctx; sentinel probe in main may pass while core ctx uses a different path
- **Proposed resolution**: Document that main's pre-core validate must use the same validate_design_tmpdir + Path.resolve sequence as core, or drop main rehydrate and validate design_tmpdir only from argv/session keys needed for the post-core sentinel probe

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_quality.py:2275-2291
- **Concern**: validator_autofix_main must build ctx only after DESIGN_TMPDIR validate/resolve. Scenario: Plan says ctx = Ctx.from_mapping right after _rehydrate_validator_env, but today resolve happens afterward (validate_design_tmpdir + Path.resolve + os.environ write). A pre-resolve ctx.design_tmpdir can differ from the path used by pause-save, autofix subprocess argv, and validator helpers.
- **Proposed resolution**: Mirror the step5c_core anchor: rehydrate, validate/resolve DESIGN_TMPDIR into os.environ and normalized_overrides, then build ctx once, then run pause/operator-cancel paths with that ctx.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:1129-1148
- **Concern**: degraded_tools_gate_main ctx merge must include parsed CLI flag values. Scenario: Parser defaults are bound from ambient os.environ at definition time; presence/binary flags arrive via --codex-present, --cursor-present, etc. Building ctx from os.environ alone (without vars(args) overrides) can ignore explicit argv and diverge from degraded_tools_result inputs.
- **Proposed resolution**: After argparse, merge vars(args) presence/binary-found fields into the ctx mapping before Ctx.from_mapping; route converted reads from that snapshot, not a pre-parse environ copy.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_summary.py:294-337
- **Concern**: render_final_summary_main needs argv-first precedence for new CLI args. Scenario: Plan adds --design-tmpdir/--issue-number/--session-id for converted cores, but render_final_summary_main currently always reads DESIGN_TMPDIR, SESSION_ID, and ISSUE_NUMBER from os.environ. If env is stale while explicit args are passed (the IPC-removal goal), render/token refresh can target the wrong tmpdir or issue metadata.
- **Proposed resolution**: Parse the new flags and apply argv-wins precedence (same pattern as plan_quality argv-first mains): use explicit args when provided, env fallback only for legacy callers.

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_quality.py:2275-2291
- **Concern**: `validator_autofix_main` builds `ctx` immediately after `_rehydrate_validator_env`, before `validate_design_tmpdir` and `Path(...).resolve()` normalize `DESIGN_TMPDIR`. Scenario: `ctx.design_tmpdir` can keep a pre-resolve or invalid tmpdir while later logic and `_validator_pause_save` use the resolved path; symlink or validation fixes diverge from the snapshot, breaking parity with the step5c normalized-wins contract and the planned symlink regression intent
- **Proposed resolution**: Mirror `step5c_core`: validate and resolve `design_tmpdir`, apply `normalized_overrides` with the resolved value, then build `ctx` once immediately before the first helper that reads via `ctx` (including `_validator_pause_save`)
