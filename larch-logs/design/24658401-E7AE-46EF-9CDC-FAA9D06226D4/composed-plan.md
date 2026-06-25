## Plan

Implement both folds with minimum surface change, and fix pause-order contracts so stdout directives never imply completed work before a terminal pause save.

- **Step 0 route fold:** make `python/cli.py design step0-route` run init work only when `ROUTE=proceed`, with route-state persisted before the pre-init pause boundary. For `ROUTE=proceed`, defer route continuation stdout until after pre-init pause and successful init so `ROUTE=proceed` never appears without init artifacts.
- **Step 1d.5 fold:** make `python/cli.py design step1d5 --mode entry` complete the no-brainstorm or already-done path itself. All skip paths write `.completed/step-1d.5` before pause. Emit `STEP1D5_ACTION` / `STEP1D5_SKIP_KIND` only after `check_pause_and_exit` returns normally.
- **Prompt thinning:** update `skills/design/SKILL.md` so removed fences are not required on dominant no-gate paths, and add `PAUSE_OK=true` terminal branches before route continuation and Step 1d.5 directive parsing.
- **Keep fallback verbs:** retain `step0-init` and `step1d5 --mode complete` for scoped branches that still need them.

## Files to modify/create

### UPDATED: python/design_lifecycle.py

Extract shared Step 0 init logic so both callers use the same implementation.

- Add a helper for feature-description materialization:
  - Inputs: `design_tmpdir`, merged wrapper env, and `init_route`.
  - Keep current behavior:
    - issue path writes `# {ISSUE_TITLE}\n\n{issue-body}`.
    - verbal fallback writes `POSITIONAL_VALUE + "\n"`.
    - only write for `init_route in {"proceed", "already-planned"}`.
- Add a helper for the init driver subprocess:
  - Run `python/cli.py design init-runparams` with current flags, including `--brainstorm-requested` from env after `BRAINSTORM_PREFIX` handling.
  - Preserve current `CONFIGURATION_ERROR_RC`, non-zero, missing result, and missing `run-params.json` checks.
  - Return parsed init result rows on success.
  - Accept a `emit_stdout: bool` (or equivalent) so the folded route path can print `INIT_STATUS` / `RENAMED` / `RUN_PARAMS_PATH` while standalone `step0_init_main` keeps clean stdout for existing tests.
- Rewrite `step0_init_main` to call those helpers:
  - Keep `check_pause_and_exit` at the start.
  - Keep existing separate wrapper behavior for already-planned replace-via-full-flow.
  - Keep wrapper stdout clean on success unless called from the folded route path.

Fold init into `step0_route_main` only for `ROUTE=proceed`.

- Keep route parsing, issue fetch, `issue-body.txt` write, route driver call, and route validation.
- After route validation, apply `BRAINSTORM_PREFIX=true` to `env["brainstorm_requested"]` before any init work (unchanged ordering relative to route KVs).
- Write `.design-step0-route-state.env` immediately after route validation and route-row construction, **before** folded init or proceed-route stdout. Leave the sidecar in place when init fails so clarify/repair flows can recover `REPO` and route metadata.
- **Stdout ordering for `ROUTE=proceed` (pause-safe):**
  - Do **not** print `ROUTE=proceed` or other proceed-continuation route rows before pre-init pause and init succeed.
  - When `route == "proceed"`:
    1. call `check_pause_and_exit` immediately before the shared init helper (restores the pause boundary `step0_init_main` used to provide between route and init).
    2. call the shared init helper with `init_route="proceed"` and stdout emission enabled.
    3. on init success only, print route continuation rows then init rows:
       - `ROUTE=proceed`
       - `HAS_CLARIFY_LABEL`, `ISSUE_NUMBER`, `ISSUE_TITLE`, optional `REPO`, optional `brainstorm_requested`
       - `INIT_STATUS`
       - `RENAMED`
       - `RUN_PARAMS_PATH`
    4. fail with the same stderr and abort wording used by `step0_init_main` when init fails; do not print `ROUTE=proceed` on init failure.
  - When pause fires at step 1, `pause_save_main` emits `PAUSE_OK=true` and exits via `check_pause_and_exit`; route-state sidecar is already written, but no `ROUTE=proceed` or init KVs are emitted.
- **Stdout for non-proceed routes** (`clarify`, `already-planned`, `resume@*`, `cancel-*`): keep current immediate route KV emission; do not run init.
- Do not run init for:
  - `clarify`
  - `already-planned`
  - `resume@*`
  - `cancel-*`

Fold Step 1d.5 skip completion into entry mode.

- In `step1d5_main --mode entry`, use this ordering:
  1. write `.completed/step-1c` and `.completed/step-1d`.
  2. read `$DESIGN_TMPDIR/run-params.json` (treat missing file as `brainstorm_requested=false`; on malformed JSON, emit a clear stderr warning and default to false only if current tests show that is existing behavior).
  3. compute skip/run internally with mutually exclusive precedence (do **not** emit `STEP1D5_*` yet):
     - if `.brainstorm-done` exists:
       - set internal action `skip`, skip kind `already-complete`.
     - elif `brainstorm_requested` is not `true`:
       - set internal action `skip`, skip kind `disabled`.
     - else (brainstorm requested and `.brainstorm-done` absent):
       - set internal action `run`.
  4. when internal action is `skip`:
     - write `.completed/step-1d.5` **before** pause check.
  5. `check_pause_and_exit`.
  6. when pause does **not** fire (function returns normally):
     - print `STEP1D5_ACTION=<skip|run>`.
     - when action is `skip`, print `STEP1D5_SKIP_KIND=<already-complete|disabled>`.
  7. timing mark.
- When pause fires at step 5, required sentinels for the computed path are already written, but **no** `STEP1D5_ACTION` / `STEP1D5_SKIP_KIND` rows are emitted.
- Keep `--mode complete` unchanged for the real brainstorm body path.
- Keep `--mode collect` unchanged.

### UPDATED: skills/design/SKILL.md

Update Step 0b prose and fences.

- In the route-driver description, state that the route wrapper also performs init work when `ROUTE=proceed`, including route-state sidecar write before the pre-init pause check and folded init inside the same fence.
- Immediately after the `step0-route` fence:
  - if fence output contains a whole-line `PAUSE_OK=true` row, treat Step 0b as a terminal pause-save boundary; stop `/design` for operator resume.
  - do not parse `ROUTE=proceed` continuation, do not assume `feature-description.txt` or `run-params.json` exist, and do not run Sub-step 6.
- In Sub-step 6:
  - **Dominant proceed-path guard (blocking):** when `ROUTE=proceed` and the `step0-route` fence stdout contains whole-line `INIT_STATUS=ok` and `RUN_PARAMS_PATH=`, **skip Sub-step 6 entirely**. Do not rewrite `feature-description.txt`, do not invoke `design init-runparams`, and do not run the `step0-init` fence. Folded init inside `step0-route` already produced those artifacts.
  - **When Sub-step 6 still runs:**
    - operator selected **replace via full flow** from the `ROUTE=already-planned` branch (the `AskUserQuestion` gate sits between route and init).
    - `ROUTE=proceed` but folded init rows are absent or incomplete (for example `INIT_STATUS=ok` or `RUN_PARAMS_PATH` missing after a non-pause route fence exit). In that case, run Sub-step 6 as the repair/fallback path: write `feature-description.txt`, then invoke `step0-init`.
  - preserve the warning that Step 2b must not draft without non-empty `feature-description.txt`.

Update Step 1d.5 prose.

- Immediately after the entry fence:
  - if fence output contains a whole-line `PAUSE_OK=true` row, treat Step 1d.5 as a terminal pause-save boundary; stop `/design` for operator resume.
  - do not parse `STEP1D5_ACTION`, do not read `brainstorm.md`, do not run `--mode complete`, and do not continue to Step 1d.7.
- When `PAUSE_OK` is absent, parse `STEP1D5_ACTION`.
- If `STEP1D5_ACTION` is missing or empty:
  - print a warning breadcrumb.
  - abort `/design` (do not continue to Step 1d.7, do not read `brainstorm.md`, do not run `--mode complete`).
- If `STEP1D5_ACTION=skip`:
  - if `STEP1D5_SKIP_KIND=already-complete`, print `⏩ 1d.5: brainstorm — skipped (already complete; .brainstorm-done present)`.
  - else print `⏩ 1d.5: brainstorm — skipped`.
  - continue directly to Step 1d.7.
  - do not read `brainstorm.md`.
  - do not run `step1d5 --mode complete`.
- If `STEP1D5_ACTION=run`:
  - read `skills/design/references/brainstorm.md`.
  - run the brainstorm body.
  - then run the existing `step1d5 --mode complete` fence before Step 1d.7.
- Remove the prompt-side instruction to read `run-params.json`; the wrapper now owns it.
- Remove the prompt-side instruction to run `step1d5 --mode complete` after skip; skip completion is owned by entry mode.

### UPDATED: python/test_design_lifecycle.py

Add and adjust tests for Step 0.

- Add a route-proceed test that verifies:
  - `step0_route_main` calls the init helper path after route succeeds.
  - `feature-description.txt` preserves `# {title}\n\n{body}`.
  - `run-params.json` exists after folded init.
  - stdout includes route KVs and init KVs together on success.
  - `.design-step0-route-state.env` exists before init is attempted.
  - `ROUTE=proceed` appears only after init succeeds (not before init subprocess).
- Add a route-proceed + `BRAINSTORM_PREFIX=true` test that verifies:
  - folded init passes `--brainstorm-requested true` to `init-runparams`.
  - `run-params.json` contains `"brainstorm_requested": true` after folded init.
- Add a non-proceed route test that verifies `clarify`, `already-planned`, and `resume@2a` do not call init.
- Add an init-failure route test that verifies:
  - the folded path aborts with the same fail-closed behavior as `step0_init_main`.
  - `.design-step0-route-state.env` remains present after init failure.
  - `ROUTE=proceed` is not printed on init failure.
- Add a route-proceed pause-boundary test that verifies:
  - with `.pause-requested` present after the mocked route driver returns, `step0_route_main` exits via `pause_save` before `init-runparams` runs.
  - stdout contains `PAUSE_OK=true`.
  - stdout does **not** contain `ROUTE=proceed` or `INIT_STATUS=`.
  - `.design-step0-route-state.env` exists.
- Update existing route tests that monkeypatch `subprocess.run` so they either:
  - return distinct fake results for `design route`, `design init-runparams`, timing, and gh calls; or
  - choose non-proceed routes when the test only covers routing.

Add tests for Step 1d.5.

- `--mode entry` with `{"brainstorm_requested": false}`:
  - writes `.completed/step-1c`, `.completed/step-1d`, and `.completed/step-1d.5`.
  - emits `STEP1D5_ACTION=skip` and `STEP1D5_SKIP_KIND=disabled`.
- `--mode entry` with `{"brainstorm_requested": false}` and `.brainstorm-done` present:
  - writes `.completed/step-1d.5`.
  - emits `STEP1D5_ACTION=skip` and `STEP1D5_SKIP_KIND=already-complete` (not `disabled`).
- `--mode entry` with `{"brainstorm_requested": true}` and `.brainstorm-done`:
  - emits `STEP1D5_SKIP_KIND=already-complete`.
- `--mode entry` with `{"brainstorm_requested": true}` and no `.brainstorm-done`:
  - does not write `.completed/step-1d.5`.
  - emits `STEP1D5_ACTION=run`.
- Extend the existing entry pause-order test so skip paths assert `.completed/step-1d.5` exists before `pause_save` runs (mirror the `--mode complete` test).
- Add an entry pause test for the disabled skip path that verifies:
  - `.completed/step-1d.5` exists before `pause_save`.
  - stdout does **not** contain `STEP1D5_ACTION=`.
- Keep the existing `--mode complete` pause-order test.

### UPDATED: scripts/test-design-structure.sh

Update structural pins for the new prompt shape.

- Keep existing pins that require:
  - bare `step0-route`.
  - bare `step1d5 --mode entry`.
  - retained `step0-init` verb.
  - retained `step1d5` verb.
- Add pins for the new Step 1d.5 directive strings in `skills/design/SKILL.md`:
  - `STEP1D5_ACTION=skip`
  - `STEP1D5_SKIP_KIND=already-complete`
  - `STEP1D5_ACTION=run`
  - missing/empty `STEP1D5_ACTION` abort branch
  - `PAUSE_OK=true` terminal branch before `STEP1D5_ACTION` parsing
- Add pins for Step 0 route pause handling in `skills/design/SKILL.md`:
  - `PAUSE_OK=true` terminal branch after the `step0-route` fence
  - Sub-step 6 init-complete guard keyed on `INIT_STATUS=ok` (not bare `ROUTE=proceed`)
  - Sub-step 6 explicit skip when `ROUTE=proceed` and `INIT_STATUS=ok` plus `RUN_PARAMS_PATH` are present (no second `step0-init` on dominant proceed path)
- Add a pin that `python/design_lifecycle.py` contains the new Step 1d.5 action KVs.
- Add a pin that `skills/design/SKILL.md` no longer describes the completion fence as "Run exactly once after skip or finish".
- Add a pin that folded route init calls `check_pause_and_exit` before the shared init helper (or equivalent structural marker in `step0_route_main`).
- Add a pin that proceed-route stdout defers `ROUTE=proceed` until after init success (or equivalent structural marker).
- Keep the existing `step1d5 --mode complete` pin implicit through CLI and launcher coverage, because it must still exist for the brainstorm path.

## Edge cases

- **Brainstorm title prefix:** ensure `BRAINSTORM_PREFIX=true` updates `env["brainstorm_requested"]` before folded init writes `run-params.json`; verify with a proceed-route pytest, not only route-state sidecar.
- **Already-planned replace:** keep the separate `step0-init` fence because `AskUserQuestion` sits between route and init.
- **Dominant proceed path:** after successful folded init (`INIT_STATUS=ok` + `RUN_PARAMS_PATH` in `step0-route` stdout), Sub-step 6 must not run; a second init would duplicate rename/run-params work or fail closed.
- **Proceed init fallback:** if `ROUTE=proceed` but init rows are missing after a non-pause route fence exit, Sub-step 6 remains the repair path via `step0-init`.
- **Resume:** route may merge flags into existing `run-params.json`, but it must not rewrite `feature-description.txt` or rerun init.
- **Clarify:** route must return `ROUTE=clarify` without init.
- **Route-state on init failure:** `.design-step0-route-state.env` must exist before init and survive init failure.
- **Pre-init pause:** on `ROUTE=proceed`, honor `.pause-requested` after the route driver returns and before rename / feature-description / run-params work; emit `PAUSE_OK=true` without `ROUTE=proceed` or init KVs.
- **Pause ordering (1d.5):** entry mode must write `.completed/step-1c`, `.completed/step-1d`, and on skip paths `.completed/step-1d.5` before pause-check; emit `STEP1D5_ACTION` only after pause returns normally.
- **Skip precedence:** when `.brainstorm-done` exists, use skip kind `already-complete` and its breadcrumb even if `brainstorm_requested` is false (resume/re-run case).
- **Disabled skip parity:** the `brainstorm_requested is not true` branch must mirror skip-tail behavior: write `.completed/step-1d.5`, then after pause passes emit `STEP1D5_ACTION=skip` and `STEP1D5_SKIP_KIND=disabled`.
- **Breadcrumbs:** preserve both skip messages exactly, including the `.brainstorm-done` variant.

## Failure modes

- If folded init fails, abort the route fence with the existing Step 0b init failure wording; leave route-state sidecar in place; do not print `ROUTE=proceed`.
- If folded init exits 0 without `INIT_STATUS=ok` and `run-params.json`, abort.
- If pre-init pause fires on `ROUTE=proceed`, emit `PAUSE_OK=true` and exit; orchestration must stop before assuming init artifacts exist.
- If orchestration runs Sub-step 6 after folded init already emitted `INIT_STATUS=ok` and `RUN_PARAMS_PATH`, duplicate init may rename twice or fail; the Sub-step 6 skip guard prevents this on the dominant proceed path.
- If Step 1d.5 cannot parse `run-params.json`, treat missing as false. For malformed JSON, prefer a clear stderr warning and default to false only if current tests show that is existing behavior.
- If Step 1d.5 pause fires after skip sentinels are written, emit `PAUSE_OK=true` without `STEP1D5_ACTION`; orchestration must stop before Step 1d.7.
- If the prompt misses `STEP1D5_ACTION` after the entry fence (and `PAUSE_OK` is absent), abort `/design` explicitly (SKILL fail-closed branch); do not continue silently.

## Testing strategy

Run focused tests first.

- `python3 -m pytest python/test_design_lifecycle.py`

Run structural coverage.

- `make test-design-structure`

Run required repo checks after changes.

- `make lint`
- If Python files changed, also run:
  - `make py-lint`
  - `make py-test`

## Acceptance

- On `ROUTE=proceed`, the `step0-route` fence writes `feature-description.txt`, performs the `[DESIGNING]` rename, writes `run-params.json`, and emits `INIT_STATUS=ok` / `RENAMED` / `RUN_PARAMS_PATH` alongside the route KVs in one fence; the dominant proceed path runs no separate `step0-init` fence.
- Non-proceed routes (`clarify`, `already-planned`, `resume@*`, `cancel-*`) return their `ROUTE` without folded init. The `already-planned` to replace-via-full-flow path still runs the separate `step0-init` fence after its `AskUserQuestion` gate.
- On `ROUTE=proceed`, a pause requested after the route driver returns emits a whole-line `PAUSE_OK=true` with no `ROUTE=proceed` and no init KVs; `.design-step0-route-state.env` exists before init and survives init failure; init failure aborts with the existing Step 0b wording and does not print `ROUTE=proceed`.
- `step1d5 --mode entry` writes `.completed/step-1c` and `.completed/step-1d`, and on skip paths `.completed/step-1d.5`, before `check_pause_and_exit`; it emits `STEP1D5_ACTION=skip|run` (and `STEP1D5_SKIP_KIND=disabled|already-complete` on skip) only after pause returns normally.
- Skip precedence: `.brainstorm-done` yields `already-complete`; `brainstorm_requested` not true yields `disabled`; brainstorm requested with no `.brainstorm-done` yields `run`. Both skip breadcrumbs are preserved verbatim. The no-brainstorm path runs no `--mode complete` fence; the brainstorm run path still runs it after the brainstorm body.
- The `step0-init` and `step1d5 --mode complete` launcher verbs remain callable for the scoped branches that still need them.
- `python3 -m pytest python/test_design_lifecycle.py`, `make test-design-structure`, `make lint`, `make py-lint`, and `make py-test` all pass.

review_status: complete
rounds_completed: 4
diff_lines: 333
