# design-route.sh

**Consumer**: `/design` Step 0b — pre-gate phase driver (resume detection, title-eligibility, re-entry guard, cancel rendering, resume env refresh, single `ROUTE=` verdict).

**Caller**: `skills/design/SKILL.md` Step 0b (after issue fetch and `REPO` resolve; before clarify / already-planned `AskUserQuestion` gates).

## Argv

| Flag | Required | Notes |
|------|----------|-------|
| `--design-tmpdir PATH` | yes | `cd … && pwd -P` |
| `--issue N` | yes | Positive integer |
| `--issue-title STR` | yes | No embedded newline/CR |
| `--issue-body-file PATH` | yes | Readable regular file; not a symlink |
| `--has-clarify-label true\|false` | yes | Orchestrator parses issue labels |
| `--claude-pid N` | yes | Positive integer |
| `--session-id STR` | yes | Empty allowed; rejects embedded newline/CR; used only as command-scoped render identity (`SESSION_ID_ARG`) |
| `--repo OWNER/REPO` | no | Forwarded from orchestrator; validated when present |

The driver does not fetch the issue body or resolve `REPO` itself. The module `SESSION_ID` remains pause-load output for `resume@*` result KVs; `--session-id` is kept in `SESSION_ID_ARG` and is never exported or assigned into module `SESSION_ID`.

## Derived / session inputs

- `$PLUGIN_ROOT/scripts/design-pause-load.sh` when the body matches the same `larch:design-pause:start` line regex as `design-pause-load.sh` (optional `${REPO:+--repo}`), followed by `write-design-current-env.sh` on valid `resume@*`.
- `scripts/lib-title-eligibility.sh`, `scripts/lib-design-reentry-guard.sh`.
- Plan markers `MARK_START` / `MARK_END` copied verbatim from `scripts/plan-block-read.sh` lines 20–21.
- `render-final-summary.sh --post-publish-only` on `cancel-title-filter` and `cancel-reentry-guard` after the result env has already been written.

## Responsibilities

1. Resume: `LOAD_OK=true` with a `STEP` present in `step-name-registry.tsv` → refresh current design env with `--issue-number "$ISSUE"`, `--claude-pid "$CLAUDE_PID"`, `--session-id "$SESSION_ID"`, optional `--repo "$REPO"`, and `--manual-requested true` only when `manual_gate_b` is true in `run-params.json`, then `ROUTE=resume@<STEP>` + resume KVs. Missing `run-params.json`, missing `jq`, or jq failure treats `manual_gate_b` as false. Env-refresh failure emits the detailed `larch_err` banner, exits `1`, and emits no `ROUTE=resume@*`. `LOAD_OK=true` without `STEP` or with an unregistered step → `ROUTE=cancel-pause-load` + `ERROR`; missing `step-name-registry.tsv` → exit `2` (configuration error, not `cancel-pause-load`); `LOAD_OK=false` or a non-zero loader exit → emit `WARN`/`ERROR`, fall through to steps 2–4 (no early `ROUTE=proceed`). The loader's stdout is the only parsed contract stream; stderr diagnostics are ignored by this parser.
2. Title-eligibility: lifecycle → write result env for `cancel-title-filter` + `TITLE_FILTER_REASON=lifecycle` + marker, emit the lifecycle reject banner with `larch_err`, render `--outcome cancelled-title-filter --mode N/A`, emit stdout KVs, and exit `0`; archival follows the same flow with the archival reject banner. Cancel render calls set command-scoped `DESIGN_TMPDIR`, `ISSUE_NUMBER="$ISSUE"`, and `SESSION_ID="$SESSION_ID_ARG"`, pass `${REPO:+--repo "$REPO"}` on both quiet branches, redirect render stdout with `>/dev/null`, and tolerate non-zero render rc.
3. Re-entry guard: `MARKER_HIT=true` → compute floor-zero remaining TTL, default `SUMMARY_MODE_STRING=N/A` (only trying jq when `run-params.json` exists and jq is available, tolerating jq failure), write result env for `cancel-reentry-guard`, emit the spurious re-entry banner with `larch_errf`, render `--outcome cancelled-reentry-guard --mode "$SUMMARY_MODE_STRING"`, emit stdout KVs, and exit `0`; miss or helper rc 2 → continue.
4. Verdict: clarify label → `clarify`; well-formed plan block → `already-planned`; else `proceed`. Malformed plan markers → absent.

**`ROUTE` verdict set** (orchestrator-validated): `proceed`, `clarify`, `already-planned`, `cancel-title-filter`, `cancel-reentry-guard`, `cancel-pause-load`, `resume@<STEP>` (registered step name).

## Result env (`.design-route-result.env`)

Allowlist: `ROUTE`, `BRAINSTORM_PREFIX`, `TITLE_FILTER_REASON`, `TITLE_FILTER_MARKER`, `MARKER_AGE`, `MARKER_TTL`, `DESIGN_REENTRY_MARKER_PATH`, `RESUME_STEP`, `SESSION_ID`, `RUN_ID`, `TIER`, `BRAINSTORM_DONE`, `WARN`, `ERROR`.

Cancel routes write and validate `.design-route-result.env` via `phase_driver_write_result_env` before any reject banner, `render-final-summary.sh`, or GitHub upsert side effect. Result-env refusal exits `1` with no render/upsert.

## Quiet child stderr bridge

Child stderr for cancel `render-final-summary.sh` and resume `write-design-current-env.sh` uses the full quiet conditional: when `[ "${LARCH_QUIET_PID:-}" = "$$" ]`, redirect stdout to `/dev/null` and stderr to FD 4 (`>/dev/null 2>&4`); otherwise redirect stdout only (`>/dev/null`). Never use unconditional `2>&4`.

## Exit codes

| Code | When |
|------|------|
| `0` | Any routing verdict, including cancel routes with `ROUTE=cancel-*` |
| `1` | `phase_driver_write_result_env` refusal or resume env-refresh failure (no `ROUTE=resume@*`) |
| `2` | Argv / body-file / repo config error |

## LLM boundary and orchestrator handoff

Stops before clarify loop and already-planned `AskUserQuestion`. The driver owns cancel render side effects and reject stderr. After the route fence exits, the orchestrator reads `ROUTE` from `$DESIGN_TMPDIR/.design-route-result.env` (file-first, symlink refusal), emits `final-summary.md` verbatim when non-empty for `cancel-title-filter` / `cancel-reentry-guard`, then always aborts before sub-step 3.

## Idempotency

Safe to re-run on the same inputs; no user prompts. Cancel render/upsert is intentionally idempotent and happens only after the result env has been accepted.

## Harness

`scripts/test-design-structure.sh` (Step 0b extracted-shape greps and route verdict anchors).

Orchestrator handoff: Step 3–shaped `set +e` capture (`_route_out`), file-first allowlisted read of `.design-route-result.env` (symlink refusal), `case` loop — routing keys via `printf -v`, `WARN`/`ERROR` printed immediately from the file-first loop before `case ROUTE`; stdout merge fills missing routing keys only; abort on exit `2` or unexpected non-zero before `ROUTE` branches. Does **not** call `phase_driver_read_result_env`.
