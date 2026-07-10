### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/agents/agent_waterfall.py:57-444
- **Concern**: [SCOPE-REDUCTION] Per-row default_model on dynamic manifest rows is unwired; review-role default is enough. Scenario: Plan tells _synthesize_dynamic_slots to write default_model=gpt-5.6-luna on rows, but Slot parsing and launch only forward global opts.default_model; row-level default_model is ignored today and the plan does not add per-slot forwarding
- **Proposed resolution**: Do not add per-row default_model fields unless agent_waterfall gains slot-level parsing and forwarding; for TRIVIAL Cursor-down emit model_role=review only and depend on CODEX_REVIEW_MODEL_DEFAULT=gpt-5.6-luna with omitted global --default-model

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/agents/_ci_launcher.py:228-341,920-1010,1043-1155
- **Concern**: [SCOPE-REDUCTION] Scope the new fix-model pins to the CI-recovery path instead of changing the shared CI launchers.. Scenario: launch-codex-ci, launch-cursor-ci, launch-claude-ci, and launch-claude-lint-fix are also used by rebase-conflict and lint-fix flows, so the new defaults would silently leak into unrelated fixers.
- **Proposed resolution**: Keep the existing shared launcher defaults for resolve-conflict and lint-fix callers, and pass the new models only from the CI-recovery call site or behind an args.role == "fix" guard.

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/agents/_ci_launcher.py:1044-1049
- **Concern**: [SCOPE-REDUCTION] The plan changes the shared Claude CI fix model without preserving the lint-fix launcher default. Scenario: `launch-claude-lint-fix` also defaults `--model` from `config.CLAUDE_CI_FIX_MODEL`, so the plan would move out-of-scope lint-fix runs from Claude Opus 4.8 to `claude-sonnet-4-6[1m]`.
- **Proposed resolution**: Split the CI-recovery Claude model from lint-fix, or override `launch_claude_lint_fix_main` to keep `claude-opus-4-8` while only CI recovery uses `claude-sonnet-4-6[1m]`.
