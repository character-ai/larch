## Plan

### Approach

- Keep the fix centered on `step0_route_main()` and `_finish_step0_route()` in `python/larch/design/design_step0.py`, per the resolved scope.
- Add a small helper, for example `_recover_resume_route_state_values(env: dict[str, str], design_tmpdir: Path) -> dict[str, str]`, that reads any pre-existing `.design-step0-route-state.env` via `phase_driver_read_result_env(..., allow_keys=ROUTE_STATE_KEYS)` (same allowlist `step0_init_main` uses) and returns merged `ISSUE_NUMBER` / `REPO` (and optionally `ISSUE_TITLE` / `HAS_CLARIFY_LABEL` when present in route-state) with non-empty `env` values winning and route-state filling gaps only.
- **Early live-env rehydration (accepted finding):** When the loaded session `env` lacks a non-empty `ISSUE_NUMBER` or `REPO`, merge recovered route-state values into the live `env` dict **before** building `route_cmd` and **before** `subprocess.run(route_cmd, ...)`. This ensures the `design route` subprocess receives non-empty `--issue` / `--repo` when the paused session’s route-state sidecar still has them, and the same merged mapping flows into `_finish_step0_route` for route-state persistence, stdout emission, and `write-design-env`.
  - Call the merge helper in `step0_route_main()` after parsed-env / argv issue binding and before `gh issue view` and `route_cmd` construction.
  - Apply recovered values with `env.setdefault(...)` or explicit gap-fill only (never overwrite non-empty `env` entries).
- Add `_refresh_resume_source_env(ctx: Step0RouteFinishContext) -> int` near the existing Step 0 route helpers.
  - Call it only when `ctx.route.startswith("resume@")`, after `.design-step0-route-state.env` is written and before `_emit_step0_route_rows`.
  - Use the **same** merged `ctx.env` values that were live during `route_cmd` (early merge already populated them); after route-state write, optionally re-read `ISSUE_NUMBER` and `REPO` from `.design-step0-route-state.env` with the same helper/allowlist as an authoritative post-write source for the `write-design-env` argv.
- In `_finish_step0_route()` for `resume@` routes:
  - Build route-state rows from the already-rehydrated `ctx.env` (no stale blanks).
  - Write `.design-step0-route-state.env`.
  - Call `_refresh_resume_source_env` before `_emit_step0_route_rows`.
- `_emit_step0_route_rows` must receive the rehydrated `ctx.env` so stdout includes non-empty `ISSUE_NUMBER=` and `REPO=` on resume.
- Build the `write-design-env` argv with `_cli_cmd(ctx.plugin_root, "session", "write-design-env", ...)`.
  - `--output`: `ctx.design_tmpdir / "source-env.sh"`
  - `--design-tmpdir`: `ctx.design_tmpdir`
  - `--session-id`: `ctx.env["SESSION_ID"]`
  - `--issue-number`: recovered / re-read `ISSUE_NUMBER`
  - `--claude-pid`: `ctx.claude_pid`
  - `--repo`: include when recovered `REPO` is non-empty.
- Prefer `proc.run(...)` from `larch.core.proc` over a new direct `subprocess.run(...)` call for `write-design-env` to avoid adding a new subprocess-ratchet baseline row.
- Pass an env that includes `CLAUDE_PLUGIN_ROOT=str(ctx.plugin_root)`, because `write-design-env` requires it when `--claude-pid` is set.
- Validate that `SESSION_ID` and recovered `ISSUE_NUMBER` are present before invoking `write-design-env`; fail early if either is missing.
- If early merge or refresh fails to recover a numeric `ISSUE_NUMBER`, print a clear Step 0b warning to stderr and return `1` before emitting `ROUTE=resume@...`.
- Do not re-run init-runparams, rename, or run-params writes on resume paths.
- Do not hand-write `source-env.sh`.
- Preserve current behavior for `proceed`, `clarify`, `already-planned`, and cancellation routes.

### Files to modify/create

### UPDATED: python/larch/design/design_step0.py

- Add `_recover_resume_route_state_values(env: dict[str, str], design_tmpdir: Path) -> dict[str, str]` that:
  - Reads pre-existing `.design-step0-route-state.env` when present.
  - Returns merged `ISSUE_NUMBER` / `REPO` (and other `ROUTE_STATE_KEYS` gap-fills as needed) with `env` precedence for non-empty values.
- In `step0_route_main()`:
  - After parsed-env / argv issue binding, when `env` lacks non-empty `ISSUE_NUMBER` or `REPO`, call the recover helper and gap-fill the live `env` dict **before** `gh issue view` and **before** `route_cmd` is built.
  - Ensure `route_cmd` `--issue` / `--repo` args use the rehydrated `env`.
  - After route-state is written, read back `ISSUE_NUMBER` and `REPO` from `.design-step0-route-state.env` with `phase_driver_read_result_env` / `ROUTE_STATE_KEYS`.
  - Use those values for the `write-design-env` argv.
  - Require non-empty `SESSION_ID` (from `ctx.env`) and non-empty recovered `ISSUE_NUMBER`.
- In `_finish_step0_route()`:
  - For `resume@` routes only: write `.design-step0-route-state.env` from rehydrated `ctx.env`, call `_refresh_resume_source_env`, then `_emit_step0_route_rows` with the same `ctx.env`.
  - Preserve current behavior for `proceed`, `clarify`, `already-planned`, and cancellation routes.

### UPDATED: python/tests/design/test_design_lifecycle.py

- Add `test_step0_route_resume_rehydrates_source_env_from_route_state`:
  - Seed a resumed Step 0 tmpdir with `source-env.sh` containing `DESIGN_TMPDIR`, `SESSION_ID`, and `CLAUDE_PLUGIN_ROOT`, but **no** `ISSUE_NUMBER` or `REPO`.
  - Pre-seed `.design-step0-route-state.env` with `ISSUE_NUMBER=42` and `REPO=owner/repo` (simulating a prior Step 0b write from the paused session).
  - Invoke `step0_route_main(...)` with a resume route (`resume@2a`) and **without** `--issue-number` / without repopulating issue fields in the loaded session env, so `ctx.env` alone cannot fix the bug before early merge.
  - Monkeypatch `design_step0.proc.run` (or delegate via the module’s `proc` import) so `session write-design-env` calls run `session_env.write_design_env_main`.
  - Assert refreshed `source-env.sh` contains `export ISSUE_NUMBER=42` and `export REPO=owner/repo`.
  - **Assert stdout** (via `capsys`) contains `ISSUE_NUMBER=42` and `REPO=owner/repo` before/alongside `ROUTE=resume@2a`.
  - Assert the stubbed `design route` subprocess received non-empty `--issue 42` and `--repo owner/repo` in `route_cmd`.
- Add `test_step0_route_resume_rehydrates_source_env_from_ctx_env` (or fold into one parametrized test):
  - Same stale `source-env.sh`, but no pre-existing route-state; monkeypatch issue resolution so `step0_route_main` binds `ISSUE_NUMBER`/`REPO` into `env` before finish.
  - Assert the post-write route-state file and refreshed `source-env.sh` both carry the resolved values.
  - Assert stdout includes non-empty `ISSUE_NUMBER` and `REPO`.
- Adjust `test_step0_route_non_proceed_routes_do_not_init` (param includes `resume@2a`) and `test_step0_route_emits_resume_step_kvs`:
  - Monkeypatch `design_step0.proc.run` (not only `subprocess.run`) to handle `session write-design-env`, or stub `_refresh_resume_source_env` explicitly on non-resume assertions.
  - For `resume@2a`, assert refresh ran (via `write-design-env` delegation or helper call).

### Edge cases

- Resume route with missing `SESSION_ID`: fail in Step 0b before Step 5c can fail with an empty publish issue.
- Resume route with missing `ISSUE_NUMBER` in both live `env` and route-state (including after early merge): fail in Step 0b; do not emit `ROUTE=resume@...` or call `write-design-env` without a numeric issue.
- Resume route with no `REPO` in live `env` or route-state: omit `--repo`; do not invent one in the helper. When `ISSUE_NUMBER` is present, `step0_route_main` may still resolve `REPO` into `env` before finish; early merge must pick up route-state `REPO` before `route_cmd` when `env` was stale.
- Pre-existing route-state with empty `ISSUE_NUMBER`/`REPO` rows: treat as absent; fail closed rather than refreshing with empty issue.
- Early merge on non-resume paths: only gap-fill missing fields; never clobber argv-resolved or freshly fetched issue/repo values.
- Existing `REPO_ROOT`, tool health booleans, and other prior writer-owned values should remain preserved by `session write-design-env` prior-file recovery.

### Failure modes

- The refresh command can fail because `CLAUDE_PLUGIN_ROOT`, `DESIGN_TMPDIR`, or `--output` validation fails. Return `1` and print stderr detail when available.
- Reading a missing or malformed route-state file on resume leaves nothing to rehydrate; fail in Step 0b with a clear warning instead of emitting `ROUTE=resume@...` with blank stdout KVs or a still-stale `source-env.sh`.
- Deferring rehydration until after `design route` leaves `route_cmd` and stdout broken even when post-route `source-env.sh` refresh would succeed; early merge prevents that.
- A test that monkeypatches only `subprocess.run` may miss the new `proc.run` seam. Update resume-route tests explicitly.
- If `source-env.sh` is absent on resume, the writer can still recreate it with the required issue and repo values from route-state. This is acceptable and safer than continuing with a missing file.

### Testing strategy

- Run targeted tests first:
  - `cd python && pytest tests/design/test_design_lifecycle.py -k "step0_route_resume_rehydrates_source_env or step0_route_non_proceed_routes_do_not_init or step0_route_emits_resume_step_kvs"`
- Run required Python validation:
  - `make py-lint`
  - `make py-test`

## Acceptance

- Run targeted tests first:
  - `cd python && pytest tests/design/test_design_lifecycle.py -k "step0_route_resume_rehydrates_source_env or step0_route_non_proceed_routes_do_not_init or step0_route_emits_resume_step_kvs"`
- Run required Python validation:
  - `make py-lint`
  - `make py-test`

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_lines: 130
