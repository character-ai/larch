# Ship PR autonomous CI-fix

**Consumer**: /implement Step 8+ on NEXT_ACTION=ci-fix.
**Contract**: Owns the main-agent CI-fix attempt guard, CI log capture, minimal repair, checks, commit, refresh, reassessment, push, and ship re-entry procedure.
**When to load**: **MANDATORY — READ ENTIRE FILE** only on NEXT_ACTION=ci-fix after fork and repo-unavailable skips are ruled out or before applying that branch's autonomous repair body. Load this before any autonomous repair step that may re-invoke `step-8-ship.sh`.

This reference retains the Python driver non-zero routing contract for exit-3 CI handoffs. The `ci-fix` action covers `first-fixer-non-health`, `ship-pr-internal-lint-fix`, `ci-local-unfixable:*`, and exact `local-unfixable`. `ci-fix-exhausted` remains operator-bail.

Read `.ship-route-exit-handoff.env` with `larch_io.read_kvs` where applicable before the procedure. When `ledger_ready=true`, call `stall-recovery record-escalation` before edits.

  1. Read `FAILED_RUN_ID` from `.ship-route-exit-handoff.env` and read `REPO` from scoped `ship-pr-state.sh`.
  1b. If `FAILED_RUN_ID` is empty, run `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" pr checks` as the fallback diagnostic path, then route to `operator-bail` or post-driver `stall` and end this procedure; do not run steps 2-12, including `FORKED_TARGET`/`REPO_UNAVAILABLE` routing, sentinel writes, `gh run-logs`, autonomous repair, commit, push, and ship re-entry.
  2. If `FORKED_TARGET=true` or `REPO_UNAVAILABLE=true`, skip autonomous edits and route to operator-bail.
  3. Use sentinel `$IMPLEMENT_TMPDIR/main-agent-ci-fix-$FAILED_RUN_ID.attempted` and counter `$IMPLEMENT_TMPDIR/main-agent-ci-fix.count`. Attempts 1-3 may run; the next arrival falls through.
  4. Write the sentinel and increment the counter before repo edits. On write failure, append Tool Failures and fall through.
  5. Capture fresh CI logs with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" gh run-logs --run-id "$FAILED_RUN_ID" --repo "$REPO" | python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" redact secrets > "$IMPLEMENT_TMPDIR/main-agent-ci-fix-$FAILED_RUN_ID.gh-run-logs.redacted.txt"`.
  6. Make the minimal repo edit from the redacted CI log and optional detail file.
  7. Run relevant checks with `python/cli.py checks run-relevant --site step8-main-agent-fix --tmpdir "$IMPLEMENT_TMPDIR"`.
  8. Stage edited files explicitly with `git add -- <paths>`.
  9. Commit via `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git commit -m "Fix CI failure (main-agent)"`.
  10. Refresh run logs with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" run-log refresh --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"`.
  11. Rerun architectural-guidelines Phase A before the next ship re-invoke when staged or durable guideline artifacts exist.
  12. Push with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" push branch`, then re-invoke `step-8-ship.sh`.
