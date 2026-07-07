# Bgjob foreground wait contract

Use this contract for long-running larch helpers that have migrated off Claude `run_in_background`.

1. Launch with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" bgjob start --step <step> --tmpdir "$TMPDIR" --budget-s <seconds> -- <command...>` from a foreground Bash tool call. The only harness-visible stdout from the launcher is `BGJOB_STATUS=STARTED STEP=<step> PGID=<n>`.
2. If the child writes step result KVs for the orchestrator to consume, truncate or recreate that merge-input env immediately before every `bgjob start`, then pass it with `--merge-result-env <path>`. A stale env from a prior attempt must never satisfy a fresh wait's required-key gate.
3. Then call `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" bgjob wait --step <step> --tmpdir "$TMPDIR" --max-wait-s 270` with tool timeout `330000`. Only wait after the matching launch printed `BGJOB_STATUS=STARTED STEP=<step> PGID=<n>`; if the launch did not print that marker, route directly to the step's failure or stall handling instead of waiting.
4. If wait prints `BGJOB_STATUS=WAIT`, the next action is another identical `bgjob wait`. Do not emit prose, read task output, use Monitor, call TaskOutput, or sleep between waits.
5. If wait prints `BGJOB_STATUS=DEAD`, route through the step's existing failure or stall handling.
6. If wait prints `BGJOB_STATUS=DONE`, read the full KV block and the result env at `$TMPDIR/bgjob/<step>.result.env` before continuing. The result env is the completion source of truth. Continue normal branch handling only when `BGJOB_RC=0` and the step's required KVs are present in the final wait output and/or result env. Treat `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, any other non-zero `BGJOB_RC`, or missing required KVs as step failure or stall.

Existing terminal sentinels remain transition compatibility markers. Never treat the `bgjob wait` shell exit code, `BGJOB_STATUS=DONE` alone, launcher stdout, or notification-time wrapper stdout as sufficient for continuation.

## Wrapper launch example

```bash
: >"$IMPLEMENT_TMPDIR/.step-5-review-merge.env"
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" bgjob start \
  --step implement-step5-review \
  --tmpdir "$IMPLEMENT_TMPDIR" \
  --budget-s 21600 \
  --merge-result-env "$IMPLEMENT_TMPDIR/.step-5-review-merge.env" \
  -- \
  bash "${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-5-review.sh" --tmpdir "$IMPLEMENT_TMPDIR"
```

Expected launcher stdout is exactly one line shaped like:

```text
BGJOB_STATUS=STARTED STEP=implement-step5-review PGID=12345
```

No banner, summary, or extra progress text may be printed by the launcher wrapper.

## Repeated wait example

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" bgjob wait \
  --step implement-step5-review \
  --tmpdir "$IMPLEMENT_TMPDIR" \
  --max-wait-s 270
```

If stdout is:

```text
BGJOB_STATUS=WAIT
ELAPSED_S=270
```

run the same wait command again immediately. Between WAITs: no prose, no Read, no Monitor, no TaskOutput, no sleep, and no alternate progress probe.

## DONE parsing example

A successful wait can print:

```text
BGJOB_STATUS=DONE
BGJOB_RC=0
BGJOB_ELAPSED_S=42
STEP=implement-step5-review
STEP5_REVIEW_STATUS=complete
```

After `DONE`, parse all rows and read `$IMPLEMENT_TMPDIR/bgjob/implement-step5-review.result.env`. The step may continue only when the required step KVs are present and valid. `DONE` plus missing required KVs is a failure or stall path, not success.

## Step 8 handoff carve-out

Do not apply the generic `BGJOB_RC=0` success gate to `ship route-exit`. Step 8 follows its handoff sidecars: the child must write the current `.step-8-ship-handoff.rc` and, when schema JSON exists, `.step-8-ship-handoff.json` before exit. The orchestrator reads those sidecars for routing rather than treating `BGJOB_RC=0` alone as success.

## Parallel external lanes

Every concurrent external lane must use a unique `--step` slug, such as `review-codex-1` and `review-cursor-1`. Shared slugs clobber registry rows, stdout/stderr logs, and `$TMPDIR/bgjob/<step>.result.env`.
