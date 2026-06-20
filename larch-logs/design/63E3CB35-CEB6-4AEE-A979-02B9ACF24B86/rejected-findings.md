### [Plan Review] FINDING_2

### FINDING_2: Launcher needs explicit bare-verb dispatch for Step 6
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan moves SKILL Step 6 fences to bare verbs (`step6`, `step6-prelude`, `step6-cleanup`) but only documents `.sh` basename remaps and a loose bare-verb allowlist grep. It does not require extending `_design_run_launcher_text` in `python/session_env.py` with a `step6|step6-prelude|step6-cleanup)` case arm that execs `python3 … design "$script"`. After SKILL changes the Step 6 fence to `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step6`, the launcher hits the final `*)` branch and returns `ERROR=unknown design wrapper verb`; cleanup never runs on the happy path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add an explicit launcher case arm for `step6|step6-prelude|step6-cleanup)` (same exec pattern as step0 bare verbs) and pin it in `scripts/test-design-structure.sh` with a `contains` check for `design step6 --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"` (mirror the Step 2 `.sh` mapping pins).


### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/session_env.py:858-868
- **Concern**: [SCOPE-REDUCTION] SKILL Step 6 fence moves to bare `step6` but the plan never specifies a design-run launcher exec branch for bare `step6` / `step6-prelude` / `step6-cleanup`. Scenario: After deleting `design-step6.sh`, `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step6` hits the default `ERROR=unknown design wrapper verb` branch; Step 6 never runs despite pytest/cli registry work
- **Proposed resolution**: Add a `step6|step6-prelude|step6-cleanup)` case that `exec python3 "$PLUGIN_ROOT/python/cli.py" design "$script" --session-env-path ...` (mirror the step0 bare-verb case); pin that routing in `scripts/test-design-structure.sh`, not only retired `.sh` basename maps

