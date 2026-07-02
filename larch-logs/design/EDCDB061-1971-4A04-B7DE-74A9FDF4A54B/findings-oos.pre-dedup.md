### OOS_1: [OUT_OF_SCOPE] Per-process unlink for validate-plan-commands mkstemp fallback
- **Description**: [OUT_OF_SCOPE] Per-process unlink for validate-plan-commands mkstemp fallback. Scenario: Outside Claude Code, `plan validate` without `DESIGN_TMPDIR` still leaves `larch-validate-plan-commands.log.*` at `$TMPDIR` top level until manual `/larch:cleanup` or a 7-day SessionStart sweep. SessionStart-only mitigation is enough for the plugin hook path; per-process try/finally is optional hardening for headless CLI.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/_plan_quality_commands.py:887
- **Phase**: design



