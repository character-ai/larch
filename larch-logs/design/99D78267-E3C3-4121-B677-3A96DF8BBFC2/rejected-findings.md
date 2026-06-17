### [Plan Review] FINDING_1

### FINDING_1: Thin-wrapper template omits script-dir plugin-root fallback  fallback
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The forward-looking thin-wrapper invocation pattern prescribed across all three proposed surfaces (AGENTS.md Conventions bullet, `.claude/rules/python-first-scripts.md`, and the new `docs/python-migration.md` Decision log entry) shows only `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py"` and omits recipe step 4’s script-dir-first plugin-root derivation. If new Bash glue wrappers are copied from those docs verbatim, they can fail when run directly from a checkout without a prehydrated `CLAUDE_PLUGIN_ROOT`, contradict the standing bash-caller rule already documented in recipe step 4 and existing thin wrappers (e.g. `skills/implement/scripts/write-final-report.sh`, `scripts/implement-preflight.sh`, `skills/implement/scripts/step-8-ship.sh`), and ship two incompatible wrapper recipes in the same PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Reuse the same thin-wrapper contract everywhere: derive plugin root from the wrapper script location first (as in scripts/implement-preflight.sh:73 and skills/implement/scripts/step-8-ship.sh:5-11), fall back to ${CLAUDE_PLUGIN_ROOT}, then delegate to python/cli.py; cross-link recipe step 4 instead of inventing a narrower template
  - From Cursor-Requirements: Align the prescribed thin-wrapper delegation pattern on all three surfaces with recipe step 4 and `write-final-report.sh`: `SCRIPT_DIR` resolution plus `PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/..." && pwd -P)}"` then `exec python3 "$PLUGIN_ROOT/python/cli.py" <domain> <verb> [args...]`; keep the amended **No shims** text scoped to migration cutover only

