### [Plan Review] FINDING_2

### FINDING_2: Step 2b caller table lacks explicit ctx ownership
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The Step 2b caller table says to pass `ctx` after normalization, but no `ctx` owner is defined. Postplan/drafter paths may build duplicate snapshots or thread a half-built `ctx` when only `Path` threading is required for this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: State explicitly that step2b_postplan_main and step2b_drafter_main pass ctx=None and only thread the entry-validated design_tmpdir Path into _shared_step2b_postplan_body; reserve Ctx builds to step5c_core and step_final_summary_core


### [Plan Review] FINDING_3

### FINDING_3: Failed-publish-tail branch missing from final_summary_path inventory
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The failed-publish-tail render path omits explicit `final_summary_path` in the call-site inventory. That branch calls `_step5c_render_final_summary(design_tmpdir, env, failed-publish-tail)` with no path arg today; removing `FINAL_SUMMARY_PATH` env IPC without a parameter can break emit/delete when `result_env` is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add the failed-publish-tail branch to the final_summary_path inventory and require str(design_tmpdir / final-summary.md) at both _step5c_render_final_summary and _emit_final_summary_marked_from_disk call sites


### [Plan Review] FINDING_4

### FINDING_4: step_final_summary_main may double-rehydrate and disagree with core on DESIGN_TMPDIR
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `step_final_summary_main` keeps pre-core rehydrate/validate while core rehydrates again. Main and core can disagree on normalized `DESIGN_TMPDIR` if only core builds `ctx`; the sentinel probe in main may pass while core `ctx` uses a different path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Document that main's pre-core validate must use the same validate_design_tmpdir + Path.resolve sequence as core, or drop main rehydrate and validate design_tmpdir only from argv/session keys needed for the post-core sentinel probe


### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/ctx.py:32-51
- **Concern**: [SCOPE-REDUCTION] `Ctx` typed fields include `implement_tmpdir`, `larch_run_id`, and `session_tmpdir` not read on any pinned conversion surface this PR. Scenario: This tranche converts design lifecycle cores, three `agents.py` owners, and three `plan_quality.py` argv-first mains; none of the listed helper conversions consume those fields. Extra typed fields expand the frozen API and invite drift before adoption
- **Proposed resolution**: Add only typed fields referenced in this PR's converted reads; defer `implement_tmpdir`, `larch_run_id`, and `session_tmpdir` until a follow-up names consumers


### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/ctx.py:32-51
- **Concern**: [SCOPE-REDUCTION] Ctx typed fields include implement_tmpdir and larch_run_id. Scenario: Pinned agents/design_lifecycle/plan_quality paths in this PR do not read those keys; unused fields expand the first-tranche API without adoption benefit
- **Proposed resolution**: Omit implement_tmpdir and larch_run_id from the initial Ctx dataclass; add typed fields only when a pinned owner in this PR reads them


### [Plan Review] FINDING_11

### FINDING_11:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/agents.py:1909-1985, python/agents.py:1988-2008
- **Concern**: [SCOPE-REDUCTION] Plan converts external_startup_lock_acquire even though the pinned run_external_agent_main owner never calls it. Scenario: The startup-lock helper is shared by launch paths the plan explicitly defers, so converting its env reads expands this tranche beyond the three pinned agents owners and risks changing deferred launch behavior
- **Proposed resolution**: Drop external_startup_lock_acquire and its startup-lock env constants/tests from this PR, or leave the helper on live os.environ until a tranche converts one of its actual callers


