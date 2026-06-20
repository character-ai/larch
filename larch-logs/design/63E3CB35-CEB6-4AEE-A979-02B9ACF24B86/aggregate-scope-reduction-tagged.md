### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/session_env.py:858-868
- **Concern**: [SCOPE-REDUCTION] SKILL Step 6 fence moves to bare `step6` but the plan never specifies a design-run launcher exec branch for bare `step6` / `step6-prelude` / `step6-cleanup`. Scenario: After deleting `design-step6.sh`, `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step6` hits the default `ERROR=unknown design wrapper verb` branch; Step 6 never runs despite pytest/cli registry work
- **Proposed resolution**: Add a `step6|step6-prelude|step6-cleanup)` case that `exec python3 "$PLUGIN_ROOT/python/cli.py" design "$script" --session-env-path ...` (mirror the step0 bare-verb case); pin that routing in `scripts/test-design-structure.sh`, not only retired `.sh` basename maps
