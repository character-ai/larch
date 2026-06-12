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
| `--partition-requested true\|false` | no | Current argv flag; defaults `false`; OR-merged into safe existing `run-params.json` for `resume@*` / `already-planned` |
| `--brainstorm-requested true\|false` | no | Current argv flag; defaults `false`; same route-only OR-merge |
| `--approve-requested true\|false` | no | Current argv flag; defaults `false`; same route-only OR-merge |
| `--skip-approve-requested true\|false` | no | Current argv flag; defaults `false`; same route-only OR-merge |
| `--repo OWNER/REPO` | no | Forwarded from orchestrator; validated when present |

The driver does not fetch the issue body or resolve `REPO` itself. The module `SESSION_ID` remains pause-load output for `resume@*` result KVs; `--session-id` is kept in `SESSION_ID_ARG` and is never exported or assigned into module `SESSION_ID`.

## Derived / session inputs

- `$PLUGIN_ROOT/scripts/design-pause-load.sh` when the body matches the same `larch:design-pause:start` line regex as `design-pause-load.sh` (optional `${REPO:+--repo}`), followed by `write-design-current-env.sh` on valid `resume@*`.
- `python/cli.py issue title-eligibility`, `scripts/lib-design-reentry-guard.sh`.
- Plan markers `MARK_START` / `MARK_END` copied verbatim from `python/cli.py plan-block read` lines 20–21.
- `render-final-summary.sh --post-publish-only` on `cancel-title-filter` and `cancel-reentry-guard` after the result env has already been written.

## Responsibilities

1. Resume: `LOAD_OK=true` with a `STEP` present in `step-name-registry.tsv` and `MARKER_CLEARED` not `false` → refresh current design env with `--issue-number "$ISSUE"`, `--claude-pid "$CLAUDE_PID"`, `--session-id "$SESSION_ID"`, and optional `--repo "$REPO"`, then `ROUTE=resume@<STEP>` + resume KVs, including loader `MARKER_CLEARED=true|false` when present. Env-refresh failure emits the detailed `larch_err` banner, exits `1`, and emits no `ROUTE=resume@*`. `LOAD_OK=true` without `STEP`, with an unregistered step, or with `MARKER_CLEARED=false` → `ROUTE=cancel-pause-load` + `ERROR`/`WARN`; missing `step-name-registry.tsv` → exit `2` (configuration error, not `cancel-pause-load`); `LOAD_OK=false` or a non-zero loader exit → `ROUTE=cancel-pause-load` + loader `WARN`/`ERROR` (no fallthrough to title/re-entry/verdict). The loader's stdout is the only parsed contract stream; stderr diagnostics are ignored by this parser.
2. Title-eligibility: lifecycle → write result env for `cancel-title-filter` + `TITLE_FILTER_REASON=lifecycle` + marker, emit the lifecycle reject banner with `larch_err`, render `--outcome cancelled-title-filter --mode N/A`, emit stdout KVs, and exit `0`; archival follows the same flow with the archival reject banner. Cancel render calls set command-scoped `DESIGN_TMPDIR`, `ISSUE_NUMBER="$ISSUE"`, and `SESSION_ID="$SESSION_ID_ARG"`, pass `${REPO:+--repo "$REPO"}` on both quiet branches, redirect render stdout with `>/dev/null`, and tolerate non-zero render rc.
3. Re-entry guard: `MARKER_HIT=true` → compute floor-zero remaining TTL, default `SUMMARY_MODE_STRING=N/A` (only trying jq when `run-params.json` exists and jq is available, tolerating jq failure), write result env for `cancel-reentry-guard`, emit the spurious re-entry banner with `larch_errf`, render `--outcome cancelled-reentry-guard --mode "$SUMMARY_MODE_STRING"`, emit stdout KVs, and exit `0`; miss or helper rc 2 → continue.
4. Verdict: clarify label → `clarify`; well-formed plan block → `already-planned`; else `proceed`. Malformed plan markers → absent. Before emitting `resume@*` or `already-planned`, `merge_router_flags()` OR-merges current `--partition`, `--brainstorm`, Brainstorm title-prefix auto-enable, `--per-round-approval`, and `--skip-approve` booleans into an existing safe `run-params.json`; jq failures append a warning entry, missing/unsafe `run-params.json` and unavailable jq emit `WARN=` breadcrumbs.

**`ROUTE` verdict set** (orchestrator-validated): `proceed`, `clarify`, `already-planned`, `cancel-title-filter`, `cancel-reentry-guard`, `cancel-pause-load`, `resume@<STEP>` (registered step name).

## Result env (`.design-route-result.env`)

Allowlist: `ROUTE`, `BRAINSTORM_PREFIX`, `TITLE_FILTER_REASON`, `TITLE_FILTER_MARKER`, `MARKER_AGE`, `MARKER_TTL`, `DESIGN_REENTRY_MARKER_PATH`, `RESUME_STEP`, `SESSION_ID`, `RUN_ID`, `BRAINSTORM_DONE`, `MARKER_CLEARED`, `WARN`, `ERROR`.

Cancel routes write and validate `.design-route-result.env` via `phase_driver_write_result_env` before any reject banner, `render-final-summary.sh`, or GitHub upsert side effect. Result-env refusal exits `1` with no render/upsert. `resume@*` / `already-planned` route-flag merge warnings are included as `WARN=` records before the result env is written.

## Quiet child stderr bridge

Child stderr for cancel `render-final-summary.sh` and resume `write-design-current-env.sh` uses the full quiet conditional: when `[ "${LARCH_QUIET_PID:-}" = "$$" ]`, redirect stdout to `/dev/null` and stderr to FD 4 (`>/dev/null 2>&4`); otherwise redirect stdout only (`>/dev/null`). Never use unconditional `2>&4`.

## Exit codes

| Code | When |
|------|------|
| `0` | Any routing verdict, including cancel routes with `ROUTE=cancel-*` |
| `1` | `phase_driver_write_result_env` refusal or resume env-refresh failure (no `ROUTE=resume@*`) |
| `2` | Argv / body-file / repo config error |

## LLM boundary and orchestrator handoff

Stops before clarify loop and already-planned `AskUserQuestion`. The driver owns cancel render side effects and reject stderr. After the route fence exits, the orchestrator reads allowlisted keys from `$DESIGN_TMPDIR/.design-route-result.env` through `scripts/read-result-env.sh` (file-first with KV-filtered stdout fallback), emits `final-summary.md` verbatim when non-empty for `cancel-title-filter` / `cancel-reentry-guard`, then always aborts before sub-step 3.

## Idempotency

Safe to re-run on the same inputs; no user prompts. Cancel render/upsert is intentionally idempotent and happens only after the result env has been accepted.

## Harness

`scripts/test-design-structure.sh` (Step 0b extracted-shape greps and route verdict anchors).

Orchestrator handoff: Step 3–shaped `set +e` capture to a stdout file, `scripts/read-result-env.sh --input "$DESIGN_TMPDIR/.design-route-result.env" --fallback-input "$_route_stdout_file"` with route-key allowlist, source the generated safe env, then branch on `ROUTE`; abort on exit `2` or unexpected non-zero before the reader. `merge_router_flags()` is driver-owned, not prompt-side Bash.
