## Goal
Implement issue #3420: [IMPLEMENTING] Round II of /design refactor, Phase 5: thin Step 0b (cancel/resume into drivers)\n\n**Context.** Part of Round II of the `/design` refactor (rationale in Phase 1). Step 0b is the heaviest inline surface in the skill..

## Implementation Plan
## Plan

# Implementation Plan — #3420: thin Step 0b (cancel/resume into drivers)

## Goal

Move the non-LLM rendering of Step 0b's two consumption fences out of `SKILL.md` and into the phase drivers, so each driver emits a single STATUS + exit code and the orchestrator fences collapse to capture → parse result-env → branch into only the genuinely-LLM routes: proceed/tier, clarify loop, already-planned prompt, resume continuation. Behavior across all seven routing outcomes is preserved; only WHERE the rendering happens moves.

## Approach

Two phase drivers already own routing/init logic and emit a result-env + stdout KV contract via `lib-phase-driver.sh` (`emit_kv`, `phase_driver_write_result_env`, `larch_err`). This change extends each driver to also own the operator-facing rendering that currently lives inline in `SKILL.md` Step 0b, then thins the `SKILL.md` fences.

Key moves:
- `design-route.sh` gains ownership of: cancel-route `render-final-summary.sh` side effects, cancel reject banners (`larch_err`/`larch_errf`), reentry-guard banner composition, and resume `write-design-current-env.sh` including `manual_gate_b` from `run-params.json`.
- `design-init-runparams.sh` gains ownership of its two failure banners: contract-drift and env-refresh-failed. It already sets `INIT_STATUS` and exits 1; it will additionally print the detailed operator message itself.
- `SKILL.md` Step 0b route fence keeps capture, exit-2/exit-1 aborts, file-first result-env read, stdout merge only inside the fence as parse fallback/validation, and `_route_valid`; add `--session-id "$SESSION_ID"` to the driver invocation.
- **Cancel handoff:** collapsed `case` bodies for `cancel-title-filter` / `cancel-reentry-guard` are **no-ops** inside the bash fence. They do not render, do not emit the summary, and do not `exit 1`. The fence ends with `exit 0` when `design-route.sh` exits 0.
- **Post-fence cancel rule:** immediately after the route bash fence, the orchestrator reads `ROUTE` file-first from `$DESIGN_TMPDIR/.design-route-result.env` with symlink refusal and allowlisted `ROUTE=` parsing. Do **not** rely on captured stdout KVs after the fence. If `ROUTE` is `cancel-title-filter` or `cancel-reentry-guard`, `/design` always stops before sub-step 3. When `[ -s "${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}" ]`, emit that file verbatim as plain chat markdown before stopping. If the file is empty or missing, still stop.
- `cancel-pause-load` keeps its orchestrator abort banner + fence `exit 1`.
- `resume@*` on `_route_rc=0` prints `resumed from STEP=` only; inline env refresh is removed from `SKILL.md`.

**Operator channel split:** reject banners are driver stderr (`larch_err`/`larch_errf`) during the bash tool call; structured summary body is orchestrator chat text after the fence when non-empty. Visible ordering is mandatory:
1. driver writes and validates result-env,
2. driver emits reject banner to Bash stderr,
3. driver runs render/upsert side effect with stdout redirected,
4. driver emits stdout KVs and exits 0,
5. orchestrator emits `final-summary.md` verbatim when non-empty,
6. orchestrator aborts `/design` unconditionally for cancel routes.

**Quiet-driver contract after `larch_quiet_init`:** every moved operator-facing banner and failure diagnostic uses `larch_err` / `larch_errf`, not raw `printf`/`echo >&2`. Child stderr from `render-final-summary.sh`, resume `write-design-current-env.sh`, and init `write-design-current-env.sh` uses the quiet-aware bridge below.

### Critical hazard — render-final-summary.sh stdout vs. the KV contract

`render-final-summary.sh --post-publish-only` prints the summary body on stdout and performs GitHub upsert + `final-summary.md` write. Driver stdout is the KV stream consumed by `_route_out=$(...)`; summary stdout MUST be redirected with `>/dev/null`. Do not use `2>&1`.

Wrap each cancel render in `set +e` / explicit rc capture / restore `set -e` or equivalent `|| true`, so a non-zero render does not abort the driver before stdout KV emit. Still emit `ROUTE=cancel-*` and the reject banner.

**Quiet child stderr bridge:** mirror `render-run-summary.sh` `emit_diag` shape. Use the full conditional, never unconditional `2>&4`:

```bash
if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
  DESIGN_TMPDIR="$DESIGN_TMPDIR" ISSUE_NUMBER="$ISSUE" SESSION_ID="$SESSION_ID_ARG" \
    render-final-summary.sh --outcome "$outcome" --mode "$mode" ${REPO:+--repo "$REPO"} --post-publish-only >/dev/null 2>&4
else
  DESIGN_TMPDIR="$DESIGN_TMPDIR" ISSUE_NUMBER="$ISSUE" SESSION_ID="$SESSION_ID_ARG" \
    render-final-summary.sh --outcome "$outcome" --mode "$mode" ${REPO:+--repo "$REPO"} --post-publish-only >/dev/null
fi
```

Apply the same conditional form to resume `write-design-current-env.sh` and init `write-design-current-env.sh`. Cancel render invocations in `design-route.sh` MUST include `${REPO:+--repo "$REPO"}` on both quiet branches so non-default-repo `/design` runs upsert and link against the bound issue, not the hub default.

**CLI flags, not env-only:** `render-final-summary.sh` requires `--outcome` and `--mode` argv. Cancel branches pass:
- `--outcome cancelled-title-filter` + `--mode N/A`
- `--outcome cancelled-reentry-guard` + tolerant `SUMMARY_MODE_STRING`

For reentry guard, `SUMMARY_MODE_STRING` defaults to `N/A`; only attempt `jq` when `run-params.json` exists and `jq` is available; tolerate jq failure and keep `N/A`.

### Result-env before side effects

On cancel routes, write and validate `$DESIGN_TMPDIR/.design-route-result.env` via `phase_driver_write_result_env` **before** any `render-final-summary.sh` call or GitHub upsert.

Refactor `emit_route_result` into helpers, e.g.:
1. `route_build_kvs` → array of KVs for current `ROUTE` / guard fields.
2. `route_write_result_env` → `phase_driver_write_result_env`; on refusal `exit 1` with no render/upsert.
3. `route_emit_cancel_side_effects` → reject `larch_err`/`larch_errf`, then command-scoped render with quiet bridge; no stdout KV emit yet.
4. `route_emit_stdout_and_exit` → `emit_kv` loop + `exit 0`.

Cancel-title-filter / cancel-reentry-guard call (2) → (3) → (4). Proceed/clarify/already-planned/resume keep the normal tail emit unless they gain cancel-like side effects.

### Session / issue identity for render and resume

`render-final-summary.sh` reads `DESIGN_TMPDIR`, `ISSUE_NUMBER`, and `SESSION_ID` from the environment. Module `SESSION_ID` remains pause-load-only for `SESSION_ID=` result-env KVs on `resume@*`; never assign argv into it.

- Add required `--session-id` argv → `SESSION_ID_ARG`.
- Add `validate_session_id_arg`: reject newline/CR only; empty string allowed. Require the flag be present. Do not use `validate_plain_scalar`, because it rejects `''`.
- Empty `SESSION_ID_ARG` preserves current `render-final-summary.sh` degradation to `RUN_ID=unknown`.
- Do **not** `export SESSION_ID="$SESSION_ID_ARG"`; invoke render with command-scoped env only.
- Cancel `render-final-summary.sh` invocations pass `${REPO:+--repo "$REPO"}` when module `REPO` is non-empty (same shape as resume/init child forwarding).
- Resume `write-design-current-env.sh` uses pause-loaded module `SESSION_ID` and preserves full identity forwarding:
  - `--issue-number "$ISSUE"`
  - `--claude-pid "$CLAUDE_PID"`
  - `--session-id "$SESSION_ID"`
  - `_wdce_resume_args+=(--manual-requested true)` when `manual_gate_b` is true (required boolean value; never bare `--manual-requested`)
  - repo forwarding via `_wdce_resume_args+=(--repo "$REPO")` or equivalent `${REPO:+--repo "$REPO"}` shape
- Resume child invocation uses the same quiet stderr bridge conditional. On failure: `larch_err` resume env-refresh text and `exit 1` before result-env write / `ROUTE=resume@*` emit.

## Files to modify/create

### UPDATED: `skills/design/scripts/design-route.sh`
- Add `--session-id STR` → `SESSION_ID_ARG` with validation: flag required; empty OK; no newline/CR.
- Refactor route result emission per result-env-before-side-effects.
- **Cancel-title-filter:** write result-env first; emit lifecycle-vs-archival reject text via `larch_err`; then command-scoped render with `--outcome cancelled-title-filter --mode N/A` and `${REPO:+--repo "$REPO"}` on both quiet branches; stdout KV emit; `exit 0`.
- **Cancel-reentry-guard:** compute `MARKER_REMAINING` floor 0; derive `SUMMARY_MODE_STRING` with default `N/A`, only jq if `run-params.json` exists and jq is available, tolerate jq failure; write result-env first; emit spurious re-entry reject via `larch_errf`; then command-scoped render with `${REPO:+--repo "$REPO"}` on both quiet branches; stdout KV emit; `exit 0`.
- Reentry guard message uses `$CLAUDE_PID` and `design_reentry_marker_path "$ISSUE" "$CLAUDE_PID"` and preserves the “delete … to override” text.
- Render invocations use full quiet conditional:
  - quiet: `>/dev/null 2>&4`
  - non-quiet: `>/dev/null` only
- Render non-zero is tolerated; route still emits `ROUTE=cancel-*`.
- **Resume `resume@*`:**
  - `manual_gate_b` jq guard; missing `run-params.json` → false.
  - build `_wdce_resume_args` preserving `--issue-number "$ISSUE"`, `--claude-pid "$CLAUDE_PID"`, `--session-id "$SESSION_ID"`, repo forwarding, and `--manual-requested`.
  - when `manual_gate_b` is true: `_wdce_resume_args+=(--manual-requested true)`; call `write-design-current-env.sh` with quiet conditional.
  - on failure: `larch_err` resume env-refresh message and `exit 1` before any `ROUTE=resume@*` result-env/emit.
  - on success: emit `ROUTE=resume@<STEP>` plus pause KVs; `exit 0`.
- `cancel-pause-load` unchanged: no summary render.
- Exit codes:
  - `0` routing verdict including cancel routes
  - `1` result-env refusal or resume env-refresh failure
  - `2` config contract

### UPDATED: `skills/design/scripts/design-route.md`
- Document `--session-id` / `SESSION_ID_ARG`: empty allowed; render identity only.
- Document result-env-before-render ordering.
- Document command-scoped render env and non-clobbering of module `SESSION_ID`.
- Document full quiet conditional for render and resume child calls; no unconditional `2>&4`.
- Document full resume identity/repo forwarding.
- Document `${REPO:+--repo "$REPO"}` on both cancel `render-final-summary.sh` quiet branches.
- Exit code table includes:
  - cancel routes `exit 0` + `ROUTE=cancel-*`
  - resume env-refresh failure `exit 1` and no `ROUTE=resume@*`
- Orchestrator handoff: driver owns render side effects + reject stderr; orchestrator reads `ROUTE` from `$DESIGN_TMPDIR/.design-route-result.env` after the fence, emits `final-summary.md` verbatim when non-empty for cancel routes, then always aborts before sub-step 3.

### UPDATED: `skills/design/scripts/design-init-runparams.sh`
- On `INIT_STATUS=env-refresh-failed`: emit detailed `larch_err` message including literal `write-design-current-env.sh failed during Step 0b env refresh` or equivalent moved text before `emit_kv` + result-env + `exit 1`.
- Wrap init `write-design-current-env.sh` child with the same quiet conditional:
  - quiet: `>/dev/null 2>&4`
  - non-quiet: `>/dev/null` only
- On `INIT_STATUS=contract-drift`: emit a scoped detailed `larch_err` banner/block that includes all of:
  - `contract drift`
  - `aborting before silent tier downgrade`
  - `bash scripts/test-write-run-params.sh`
- No change to env-before-rename ordering, rename best-effort warn, `write-run-params.sh`, or router-flag jq-merge.

### UPDATED: `skills/design/scripts/design-init-runparams.md`
- Driver prints contract-drift and env-refresh-failed via `larch_err`.
- Driver preserves init child diagnostics under quiet mode via the same `LARCH_QUIET_PID == $$` / FD 4 bridge.
- Orchestrator propagates status + exit with short generic abort only.

### UPDATED: `skills/design/SKILL.md`
- Sub-step 2.5 intro: cancel reject banners and resume env refresh live in `design-route.sh`; orchestrator post-fence reads route from `.design-route-result.env`, emits `final-summary.md` when cancel route and non-empty, then aborts unconditionally for cancel routes; `cancel-pause-load` still aborts in fence; `AskUserQuestion` gates only.
- Route fence:
  - add `--session-id "$SESSION_ID"` to `design-route.sh`.
  - keep capture, exit-2 abort, `_route_rc` non-zero abort, file-first `.design-route-result.env` read, stdout merge only as in-fence fallback/validation, `_route_valid`, and brainstorm info banner.
  - `_route_rc` non-zero abort covers resume refresh `exit 1`, relying on driver `larch_err` for detail.
- Collapse `case "$ROUTE"`:
  - `cancel-title-filter` / `cancel-reentry-guard` → no-op only; comment says side effects + stderr live in driver and post-fence handles final-summary emit/abort.
  - no `exit 1` in those two cancel case bodies.
  - `cancel-pause-load` → orchestrator abort + `exit 1`.
  - `resume@*` → print `resumed from STEP=` only.
  - fence exits 0 when driver succeeded, including cancel routes.
- Post-fence prose immediately after the route bash fence:
  - Read `$DESIGN_TMPDIR/.design-route-result.env` directly, with symlink refusal, and parse allowlisted `ROUTE=`.
  - Do not rely on `_route_out` or merged stdout KVs after the fence.
  - If `ROUTE` is `cancel-title-filter` or `cancel-reentry-guard`, then:
    - if `[ -s "${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}" ]`, read and emit the full body verbatim as plain chat markdown.
    - always terminate `/design` before sub-step 3, even if the summary file is empty/missing or render failed.
  - State explicitly that cancel routes expect fence `exit 0`; summary emit is mandatory when the file is non-empty; abort happens after emit, not before.
- Sub-step 6 init fence:
  - drop inline detailed contract-drift / env-refresh-failed banners.
  - keep short generic `design-init-runparams.sh failed (INIT_STATUS=…)` abort relying on driver stderr.

### UPDATED: `scripts/test-design-structure.sh`
- Contract-drift pins:
  - replace broad `$SKILL_MD` contains checks with a scoped `$DESIGN_INIT_SH` check on one line/block containing `contract drift`, `aborting before silent tier downgrade`, and `bash scripts/test-write-run-params.sh`.
- Env-refresh-failed pins:
  - move detailed banner pin to `$DESIGN_INIT_SH` with literal `write-design-current-env.sh failed during Step 0b env refresh` or `larch_err` equivalent.
  - add `$DESIGN_INIT_SH` pins for `[ "${LARCH_QUIET_PID:-}" = "$$" ]` and `2>&4` tied to init `write-design-current-env.sh`.
  - keep only generic init-failure prose in `$SKILL_MD`.
- Resume pins:
  - delete from `step0b_block`: `_wdce_resume_args`, repo forwarding, `_wdce_resume_rc=$?`, resume env-refresh failure detail, `manual_gate_b`, `--manual-requested`.
  - add `$DESIGN_ROUTE_SH` pins for `_wdce_resume_args` or equivalent argv array, `--issue-number "$ISSUE"`, `--claude-pid "$CLAUDE_PID"`, `--session-id "$SESSION_ID"`, repo forwarding, `manual_gate_b`, `--manual-requested true`, `_wdce_resume_rc=$?`, resume `larch_err` text, and ordering showing `exit 1` before `ROUTE=resume@` / result emit.
  - add no-comment-only `$DESIGN_ROUTE_SH` pins tying resume `write-design-current-env.sh` to `[ "${LARCH_QUIET_PID:-}" = "$$" ]` and `2>&4`.
- Check 20:
  - delete `$SKILL_MD` pins for `issue title starts with managed lifecycle marker` and `issue title matches archival report-prefix`.
  - add `$DESIGN_ROUTE_SH` `grep -Fq` pins for those exact literals or `larch_err`/`larch_errf` wrapped equivalents.
  - keep `$SKILL_MD` `cancelled-title-filter` enum, cancel-before-clarify ordering, and brainstorm info banner.
- Check 26:
  - delete `$SKILL_MD` pins for the spurious re-entry banner and override hint.
  - add `$DESIGN_ROUTE_SH` pins for the full spurious re-entry string in post-move `$CLAUDE_PID` form and `delete ${DESIGN_REENTRY_MARKER_PATH} to override.`
- `step0b_block`:
  - pin `--session-id "$SESSION_ID"` on `design-route.sh`.
  - pin post-fence prose outside the bash fence that reads `$DESIGN_TMPDIR/.design-route-result.env`, refuses symlinks, handles cancel `ROUTE`, includes exact gate `[ -s "${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}" ]`, and says cancel routes always terminate before sub-step 3.
  - pin that cancel case bodies do not contain `exit 1`.
  - keep `cancel-pause-load` banner in `$SKILL_MD`.
- Add `$DESIGN_ROUTE_SH` pins:
  - `SESSION_ID_ARG`
  - command-scoped `ISSUE_NUMBER="$ISSUE"` on render line
  - `render-final-summary.sh` with `--outcome`, `--mode`, and `>/dev/null`
  - `${REPO:+--repo "$REPO"}` on both cancel `render-final-summary.sh` quiet branches
  - full quiet conditional `[ "${LARCH_QUIET_PID:-}" = "$$" ]` + `2>&4`
  - reject `larch_err`/`larch_errf` before `render-final-summary.sh`
  - `phase_driver_write_result_env` before reject/render on cancel paths
  - tolerant `SUMMARY_MODE_STRING=N/A` fallback for missing run-params/jq/jq failure
- Keep unchanged:
  - FINDING_2 capture/result-env pins
  - FINDING_3 exit-2 prose
  - FINDING_9 generic abort prose
  - FINDING_5 cancel-pause-load
  - Check 24 ordering
  - env-before-rename ordering

### UPDATED: `scripts/test-step0b-router-flag-recovery.sh`
- No new `design-route.sh` fixtures or thinned-fence assertions.
- Continue to exercise `design-init-runparams.sh` router-flag jq-merge only.
- Update only if an existing invocation must thread a new flag; none expected for route `--session-id`.

## Edge cases

- **SESSION_ID split:** `SESSION_ID_ARG` for render only; module `SESSION_ID` pause-load-only; never export/assign cancel argv into module `SESSION_ID`.
- **Empty SESSION_ID_ARG:** allowed at argv parse; render uses `RUN_ID=unknown` fallback.
- **Non-default REPO on cancel:** driver passes `${REPO:+--repo "$REPO"}` on both cancel render branches so summary upsert and issue URLs target the bound repo.
- **Cancel abort:** cancel-title-filter and cancel-reentry-guard always stop `/design` before sub-step 3, regardless of render success or summary file size.
- **Cancel summary emit:** orchestrator emits when file non-empty; gate on post-fence result-env `ROUTE`, not fence failure or stdout capture.
- **Post-fence source:** post-fence logic reads `$DESIGN_TMPDIR/.design-route-result.env`; stdout merge is in-fence only.
- **Result-env refusal:** no render/GitHub upsert when `phase_driver_write_result_env` fails.
- **Render stdout pollution:** redirect stdout only; KV stream stays clean.
- **Render non-zero under set -e:** tolerate render failure and still emit route KVs.
- **Empty final-summary.md:** skip summary body; operator still sees driver reject banner; `/design` still aborts.
- **Resume env-refresh failure:** driver exits 1, no `ROUTE=resume@*`; orchestrator generic `_route_rc` abort; child stderr bridged under quiet.
- **Init env-refresh failure:** driver exits 1 with detailed `larch_err`; child stderr bridged under quiet.
- **manual_gate_b missing run-params.json:** treat as false.
- **Resume manual flag:** append `--manual-requested true` only when `manual_gate_b` is true; never bare `--manual-requested` (writer requires a boolean value).
- **Reentry mode missing run-params/jq failure:** use `N/A`.
- **Operator message order:** result-env, reject stderr, render/upsert, stdout KVs, post-fence summary, abort.
- **cancel-pause-load:** no driver summary; orchestrator banner only; fence exits 1.
- **Brainstorm-prefix banner:** stays orchestrator-side.
- **Stale docs:** grep `docs/`, `README.md`, `SECURITY.md` for inline Step 0b cancel/resume rendering references.

## Failure modes

- **KV stream pollution:** mitigation: render stdout `>/dev/null`; allowlisted KV emit only.
- **Summary emitted before rejection:** mitigation: driver ordering is result-env → `larch_err`/`larch_errf` reject → render → stdout KVs; tests pin order.
- **Cancel accidentally continues:** mitigation: post-fence rule always aborts for cancel routes, independent of summary file presence.
- **Post-fence route unavailable:** mitigation: read `.design-route-result.env` file-first after fence with symlink refusal; do not rely on captured stdout.
- **Lost GitHub upsert:** keep `--post-publish-only`, redirect stdout only.
- **Lost renderer/resume/init diagnostics:** mitigation: full quiet conditional with `2>&4` only under quiet mode.
- **Invalid FD 4 use:** mitigation: never use unconditional `2>&4`; non-quiet branch redirects stdout only.
- **Wrong-repo cancel upsert:** mitigation: `${REPO:+--repo "$REPO"}` on both cancel render branches; structure pin on render argv.
- **Resume argv misparsing:** mitigation: `--manual-requested true` with explicit value; pins reject bare flag.
- **Side effects without contract:** mitigation: write result-env first; exit 1 on refusal before render/upsert.
- **SESSION_ID clobber:** mitigation: command-scoped render env only.
- **Resume identity loss:** mitigation: preserve issue, Claude PID, session ID, repo, and manual-requested argv; structural pins.
- **Reentry guard aborts before route emit due to jq/run-params absence:** mitigation: tolerant `N/A` fallback.
- **Pin under-coverage:** mitigation: exact moved literals and scoped block checks in `$DESIGN_ROUTE_SH` / `$DESIGN_INIT_SH`; delete obsolete `$SKILL_MD` pins.

## Testing strategy

- `bash scripts/test-design-structure.sh` — reframed pins per Files section:
  - exact literal migrations
  - scoped contract-drift banner
  - post-fence result-env read
  - unconditional cancel abort before sub-step 3
  - summary `-s` gate
  - cancel no `exit 1` in fence
  - route/init quiet `2>&4` conditionals
  - resume identity/repo forwarding
  - cancel render `${REPO:+--repo "$REPO"}`
  - resume `--manual-requested true`
  - result-env-before-reject/render ordering
- `bash scripts/test-step0b-router-flag-recovery.sh` — router-flag recovery only, unchanged scope.
- Driver smoke:
  - `design-route.sh --help`
  - proceed
  - cancel-title-filter
  - cancel-reentry-guard with and without `run-params.json`
  - resume success
  - resume env-refresh failure
  - KV stdout has no summary body
  - cancel exits 0
  - resume failure exits 1 and emits no `ROUTE=resume@*`
  - result-env exists before `final-summary.md` on cancel dry-run
- Init smoke:
  - env-refresh failure shows moved banner
  - quiet mode surfaces child diagnostics through FD 4
  - contract drift banner includes repro command
- `make lint` including shellcheck, bash 3.2, agent-lint S030, markdownlint.
- No new harness files.


## Acceptance

- `design-route.sh` owns cancel-title-filter / cancel-reentry-guard summary rendering (`render-final-summary.sh`, stdout redirected via the quiet FD-4 bridge), the reentry-guard banner composition, and the resume `write-design-current-env.sh` refresh. It accepts a required `--session-id` (empty allowed; newline/CR rejected). Cancel render invocations forward `${REPO:+--repo "$REPO"}` on both quiet branches; resume forwards `--manual-requested true` (never the bare flag). Result-env is written and validated before any render or GitHub upsert side effect; result-env refusal exits 1 with no side effect.
- `design-init-runparams.sh` prints the contract-drift and env-refresh-failed operator messages itself (`larch_err`, quiet FD-4 bridge for child `write-design-current-env.sh` stderr); env-before-rename ordering and the router-flag jq-merge are unchanged.
- `skills/design/SKILL.md` Step 0b route and init consumption fences are thinned to capture → file-first result-env read → branch into only the LLM routes (proceed/tier, clarify, already-planned, resume). The post-fence cancel rule reads `ROUTE` from `.design-route-result.env` (symlink refusal), emits `final-summary.md` verbatim when `[ -s … ]`, and always aborts before sub-step 3. The driver exit-code contract (0/1/2) and all seven routing outcomes (proceed/clarify/already-planned/cancel-title-filter/cancel-reentry-guard/cancel-pause-load/resume) are behavior-preserved.
- `scripts/test-design-structure.sh` FINDING_2-family pins reframed: moved banners and rendering asserted in the drivers (`$DESIGN_ROUTE_SH` / `$DESIGN_INIT_SH`); FINDING_2 capture/result-env primitives, FINDING_3 exit-2 prose, FINDING_9 generic abort prose, FINDING_5 cancel-pause-load, Check 24 ordering, and env-before-rename ordering preserved in `$SKILL_MD`.
- `scripts/test-step0b-router-flag-recovery.sh` keeps exercising the `design-init-runparams.sh` router-flag jq-merge only — no new route-driver / thin-fence fixtures (tracked as scope note #3508).
- No new harness files. `bash scripts/test-design-structure.sh`, `bash scripts/test-step0b-router-flag-recovery.sh`, and `make lint` all pass.

diff_lines: 700

## Test plan
(no test plan section in plan-file)
