### [Plan Review] FINDING_3

### FINDING_3: Empty SESSION_ID operator warning contract may be dropped
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Current `test-design-clarify.sh:198` requires publish stdout to contain `SESSION_ID missing`. Bash prints `**⚠ /design: SESSION_ID missing; skipping design log publish**`. The plan moves publish behavior to Python tests but only says empty `SESSION_ID` skips publish/rename; it never requires preserving that warning. If the shell harness drops line 198 before Python owns the check, the operator-visible contract is lost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Current test-design-clarify.sh requires publish stdout to contain SESSION_ID missing (line 198). Bash prints **⚠ /design: SESSION_ID missing; skipping design log publish**. Plan moves publish behavior to Python tests but only says empty SESSION_ID skips publish/rename; it never requires preserving that warning. Shell harness scope also drops this assertion. Add the warning to the Python publish contract and test list (assert stdout contains SESSION_ID missing). If the shell harness no longer covers publish, drop line 198 only after the Python test owns the check.


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/design-clarify.sh (plan.txt:238-240)
- **Concern**: [SCOPE-REDUCTION] Wrapper still sources --session-env-path and requires DESIGN_TMPDIR before delegating. Scenario: The plan requires Python trusted symlink handling, but shell sourcing can execute an untrusted session env target and override CLAUDE_PLUGIN_ROOT before python/cli.py design clarify runs
- **Proposed resolution**: Remove wrapper session-env sourcing and DESIGN_TMPDIR validation; compute CLAUDE_PLUGIN_ROOT from launcher env or SCRIPT_DIR, forward --session-env-path and --claude-pid, and update the wrapper harness to assert Python owns session env loading

