# Bgjob foreground wait contract

Use this contract for long-running larch helpers that have migrated off Claude `run_in_background`.

1. Launch with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" bgjob start --step <step> --tmpdir "$TMPDIR" --budget-s <seconds> -- <command...>` from a foreground Bash tool call. The only harness-visible stdout from the launcher is `BGJOB_STATUS=STARTED STEP=<step> PGID=<n>`.
2. Then call `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" bgjob wait --step <step> --tmpdir "$TMPDIR" --max-wait-s 270` with tool timeout `330000`.
3. If wait prints `BGJOB_STATUS=WAIT`, the next action is another identical `bgjob wait`. Do not emit prose, read task output, use Monitor, call TaskOutput, or sleep between waits.
4. If wait prints `BGJOB_STATUS=DEAD`, route through the step's existing failure or stall handling.
5. If wait prints `BGJOB_STATUS=DONE`, parse the full KV block before continuing. Continue normal branch handling only when `BGJOB_RC=0` and the step's required KVs are present. Treat `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, any other non-zero `BGJOB_RC`, or missing required KVs as step failure or stall.

Existing terminal sentinels remain transition compatibility markers. The bgjob result env under `$TMPDIR/bgjob/<step>.result.env` is the completion source of truth for migrated callers.
