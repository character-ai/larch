### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/python-migration.md:36-42
- **Concern**: Thin-wrapper invocation template on all three proposed surfaces shows only python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" and omits recipe step 4 plugin-root derivation. Scenario: New forward-looking thin wrappers copied from AGENTS.md / .claude/rules/python-first-scripts.md / the new decision-log bullet can fail when run directly from a checkout without a prehydrated CLAUDE_PLUGIN_ROOT, and they contradict the standing bash-caller rule already in recipe step 4
- **Proposed resolution**: Reuse the same thin-wrapper contract everywhere: derive plugin root from the wrapper script location first (as in scripts/implement-preflight.sh:73 and skills/implement/scripts/step-8-ship.sh:5-11), fall back to ${CLAUDE_PLUGIN_ROOT}, then delegate to python/cli.py; cross-link recipe step 4 instead of inventing a narrower template

### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:22-23,41,58
- **Concern**: docs-only thin-wrapper template uses only `${CLAUDE_PLUGIN_ROOT}/python/cli.py` and omits script-dir-first PLUGIN_ROOT fallback. Scenario: Per `docs/python-migration.md` recipe step 4 and existing thin wrappers such as `skills/implement/scripts/write-final-report.sh`, bash callers derive plugin root from `SCRIPT_DIR` with `${CLAUDE_PLUGIN_ROOT:-...}` before `exec python3`. If AGENTS.md, `.claude/rules/python-first-scripts.md`, and the new decision-log bullet copy the plan's shorter template verbatim, new glue wrappers may fail when run from a checkout without a prehydrated `CLAUDE_PLUGIN_ROOT`, and the same PR will ship two incompatible wrapper recipes
- **Proposed resolution**: Align the prescribed thin-wrapper delegation pattern on all three surfaces with recipe step 4 and `write-final-report.sh`: `SCRIPT_DIR` resolution plus `PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/..." && pwd -P)}"` then `exec python3 "$PLUGIN_ROOT/python/cli.py" <domain> <verb> [args...]`; keep the amended **No shims** text scoped to migration cutover only

