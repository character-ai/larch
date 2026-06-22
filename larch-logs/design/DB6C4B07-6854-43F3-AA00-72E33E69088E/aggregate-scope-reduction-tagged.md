### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/plan_quality.py:999-1243
- **Concern**: [SCOPE-REDUCTION] Grouping `validate_plan_main` / `check_plan_size_main` with `validator_autofix_main` under one `{**os.environ, **rehydrate_merged, **argv_overrides}` recipe is ambiguous. Scenario: Only `validator_autofix_main` calls `_rehydrate_validator_env` today; the other two are direct CLI/harness entrypoints with no wrapper session file. Applying validator rehydrate (or the wrong allowlist defaults) to `validate_plan_main` / `check_plan_size_main` would change `DESIGN_TMPDIR`, `SITE`, and validator-status precedence on standalone `plan validate` / `plan check-size` calls
- **Proposed resolution**: Split the plan: `validator_autofix_main` keeps `_rehydrate_validator_env` then ctx merge; `validate_plan_main` and `check_plan_size_main` build ctx from `{**os.environ, **argv_overrides}` only (no validator rehydrate)

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/ctx.py:32-51
- **Concern**: [SCOPE-REDUCTION] `Ctx` typed fields include `implement_tmpdir`, `larch_run_id`, and `session_tmpdir` not read on any pinned conversion surface this PR. Scenario: This tranche converts design lifecycle cores, three `agents.py` owners, and three `plan_quality.py` argv-first mains; none of the listed helper conversions consume those fields. Extra typed fields expand the frozen API and invite drift before adoption
- **Proposed resolution**: Add only typed fields referenced in this PR's converted reads; defer `implement_tmpdir`, `larch_run_id`, and `session_tmpdir` until a follow-up names consumers

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/ctx.py:32-51
- **Concern**: [SCOPE-REDUCTION] Ctx typed fields include implement_tmpdir and larch_run_id. Scenario: Pinned agents/design_lifecycle/plan_quality paths in this PR do not read those keys; unused fields expand the first-tranche API without adoption benefit
- **Proposed resolution**: Omit implement_tmpdir and larch_run_id from the initial Ctx dataclass; add typed fields only when a pinned owner in this PR reads them

### FINDING_12:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/agents.py:1909-1985, python/agents.py:1988-2008
- **Concern**: [SCOPE-REDUCTION] Plan converts external_startup_lock_acquire even though the pinned run_external_agent_main owner never calls it. Scenario: The startup-lock helper is shared by launch paths the plan explicitly defers, so converting its env reads expands this tranche beyond the three pinned agents owners and risks changing deferred launch behavior
- **Proposed resolution**: Drop external_startup_lock_acquire and its startup-lock env constants/tests from this PR, or leave the helper on live os.environ until a tranche converts one of its actual callers
