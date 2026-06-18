### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/design-clarify.sh (plan.txt:238-240)
- **Concern**: [SCOPE-REDUCTION] Wrapper still sources --session-env-path and requires DESIGN_TMPDIR before delegating. Scenario: The plan requires Python trusted symlink handling, but shell sourcing can execute an untrusted session env target and override CLAUDE_PLUGIN_ROOT before python/cli.py design clarify runs
- **Proposed resolution**: Remove wrapper session-env sourcing and DESIGN_TMPDIR validation; compute CLAUDE_PLUGIN_ROOT from launcher env or SCRIPT_DIR, forward --session-env-path and --claude-pid, and update the wrapper harness to assert Python owns session env loading
