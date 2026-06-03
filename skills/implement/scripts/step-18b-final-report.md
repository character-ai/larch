# step-18b-final-report.sh

`step-18b-final-report.sh` is the Step 18b mechanical wrapper for token-report refresh, `write-final-report.sh` invocation, and the `EMIT_BODY` emit decision. The `/implement` orchestrator calls it once per Step 18b entry; it never emits `summary-final.md` to chat and never writes `$IMPLEMENT_TMPDIR/.step17-emitted` (NEVER #20 boundary).

## Invocation

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-18b-final-report.sh" \
  --implement-tmpdir "$IMPLEMENT_TMPDIR"
```

`--implement-tmpdir` is required and must exist.

## Session rehydration

When `$IMPLEMENT_TMPDIR/session-env.sh` exists, the wrapper exports `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, and `LARCH_TIMING_LEDGER` from that file (same keys as the prior inline Step 18 block). When `CLAUDE_PLUGIN_ROOT` is unset, it sources `$IMPLEMENT_TMPDIR/plugin-root.env` when present.

## Rooted helper paths

All snapshot, compare, and report paths are under `$IMPLEMENT_TMPDIR/` (never cwd-relative):

| Artifact | Path |
|---|---|
| Token report JSON | `$IMPLEMENT_TMPDIR/token-report-rendered.json` |
| Pre-write body snapshot | `$IMPLEMENT_TMPDIR/.step18-prebody` |
| Final summary body | `$IMPLEMENT_TMPDIR/summary-final.md` |
| Step 17 emit sentinel (read-only) | `$IMPLEMENT_TMPDIR/.step17-emitted` |
| Token-report failure log | `$IMPLEMENT_TMPDIR/step18-token-report.failure.log` |
| write-final-report failure log | `$IMPLEMENT_TMPDIR/step18-write-final-report.failure.log` |

Helpers invoked with rooted paths:

- `"$PLUGIN_ROOT/scripts/token-report.sh" --full --format json --output "$tmpdir/token-report-rendered.json"`
- `"$SCRIPT_DIR/write-final-report.sh" --implement-tmpdir "$tmpdir"` (no `--print-stdout`)

Non-zero helper exits are captured to the failure logs above and appended with `append-tool-failure.sh` (best-effort); the wrapper continues.

## Emit decision

1. Candidate `emit_body=true` when `$IMPLEMENT_TMPDIR/.step17-emitted` is absent.
2. Snapshot `summary-final.md` to `.step18-prebody` when it exists before `write-final-report.sh`; emit `SNAPSHOT_OK` as `true` (copy succeeded), `false` (copy failed), or `absent` (no pre-write body).
3. Record `WFR_RC` from `write-final-report.sh`.
4. When `WFR_RC=0` and `summary-final.md` is non-empty and the prior candidate was false: promote to true when `SNAPSHOT_OK=absent` (no pre-write body), when `SNAPSHOT_OK=true` and `cmp` reports a difference, or when `SNAPSHOT_OK=false` (failed snapshot with `.step17-emitted` present). The snapshot-failure path fails open so a successful refreshed report body is still visible.
5. **Final gate:** emit `EMIT_BODY=true` only when candidate is true **and** `WFR_RC=0` **and** `summary-final.md` is non-empty; otherwise `EMIT_BODY=false`.

Intentional delta vs the retired inline block: the wrapper does not pass `--print-stdout` to `write-final-report.sh`, so the report body appears once at top chat (orchestrator verbatim emit) instead of also in the collapsible Bash stdout. Body file content is unchanged (`write-final-report.sh` writes `summary-final.md` regardless of `--print-stdout`).

## Emitted KVs

| KV | Meaning |
|---|---|
| `EMIT_BODY` | `true` or `false` — orchestrator verbatim emit gate |
| `WFR_RC` | Exit code from `write-final-report.sh` |
| `STEP17_EMITTED_PRESENT` | Informational only: `true` when `.step17-emitted` existed at entry (not an emit gate; `EMIT_BODY` encodes the sentinel decision) |
| `SNAPSHOT_OK` | `true`, `false`, or `absent` — pre-write snapshot outcome (see emit decision step 4) |

## Caller

`skills/implement/SKILL.md` Step 18b — parse stdout KVs, then emit `summary-final.md` verbatim only when `EMIT_BODY=true` and `WFR_RC=0` and the body file is non-empty.

## Harness

`skills/implement/scripts/test-step-18b-final-report.sh` (contract: `test-step-18b-final-report.md`).

## Edit in sync

Change this file when altering argv, rehydration keys, rooted paths, the `EMIT_BODY` gate, or failure capture behavior in `step-18b-final-report.sh`.
