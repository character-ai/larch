# scripts/step-telemetry-mark.sh — contract

## Purpose

Collapse the repeated `/implement` step-ENTRY telemetry preamble (three `read-session-env-key.sh` reads, three-key `export`, `token-ledger.sh mark`, `timing-ledger.sh mark`) into one never-fatal helper call.

## Interface

- `--implement-tmpdir DIR` — `$IMPLEMENT_TMPDIR` for this run (may be omitted; see never-fatal behavior).
- `--label TEXT` — mark label passed verbatim to both ledger scripts (may be empty).

Unknown flags are ignored. The script uses `SCRIPT_DIR` siblings (`read-session-env-key.sh`, `token-ledger.sh`, `timing-ledger.sh`) and does not require `CLAUDE_PLUGIN_ROOT`.

## Invariants

- **`set -uo pipefail` without `-e`** — pure telemetry; sibling failures must not abort the orchestrator.
- **`IMPLEMENT_TMPDIR=""` and `LABEL=""` before the arg loop** — omitted `--implement-tmpdir` must not trip `set -u` on `"${IMPLEMENT_TMPDIR:-}/session-env.sh"`.
- **Always `exit 0`** — even when `session-env.sh` is missing, keys are empty, or `--label` is omitted.
- **Git-executable (`0755`)** — `skills/implement/SKILL.md` invokes this script by direct path; mode `0644` returns 126 and `|| true` at call sites would silently drop marks.

## Env keys

Reads from `$IMPLEMENT_TMPDIR/session-env.sh` (when tmpdir is set and file exists):

- `LARCH_TOKEN_SESSION_ID`
- `LARCH_CLAUDE_SOURCE_FILE`
- `LARCH_TIMING_LEDGER`

Exports `IMPLEMENT_TMPDIR` plus those three keys before calling the ledger scripts so `timing-ledger.sh`'s `IMPLEMENT_TMPDIR` fallback matches the old inline fence.

## `/implement` callers

Converted step-ENTRY sites in `skills/implement/SKILL.md` (Steps 5, 16, 17, 18-cleanup):

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/step-telemetry-mark.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step N — name" || true
```

Each converted fence keeps `IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"`, `export IMPLEMENT_TMPDIR`, and the `plugin-root.env` source guard above the helper call.

## Out of scope

- **Step 2** — conditional `token-ledger.sh mark` inside the coder `case` (helper emits both marks unconditionally).
- **Step 18 closing `Step 18 — done` cap** — must stay orchestrator-emitted after `--since-last-mark --terse` (vendor-table slicing).
- **Trio-only rehydrate-for-children sites** — read/export keys but emit no marks.

## Makefile / harness

- `make test-step-telemetry-mark` → `scripts/test-step-telemetry-mark.sh`
- Structural coupling with converted fences: `make test-implement-timing-rehydration`
