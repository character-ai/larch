## Goal
Implement issue #4677: [IMPLEMENTING] sh-to-py G6.4: Step 5c publish-tail port.

## Implementation Plan
## Plan

### Approach

- Treat the supplied `NO_SKETCHES` synthesis as authoritative. Draft from direct repository inspection.
- Respect the round-1 constraints:
  - Keep `review_provenance` importable from `python/design_publish.py`.
  - Keep `python/cli.py design publish` available as a legacy/internal verb.
  - Add the new Step 5c entrypoint at `python/cli.py design step5c`.
  - Preserve Step 5c stdout rows, final-summary markers, sidecar handoff, status env, sentinels, and exit-code behavior.
- Keep the change minimal:
  - Do not physically merge `design_publish.py` into `design_lifecycle.py`.
  - Refactor only enough publish code to call it in-process.
  - Keep existing publish tests and add lifecycle tests for wrapper orchestration.
- Testing strategy (accepted harness findings — no publish stub seam):
  - Narrow `skills/design/scripts/test-design-step5c.sh` to thin-wrapper delegation smoke only.
  - Do **not** add `DESIGN_PUBLISH_STUB_RC` / `DESIGN_PUBLISH_STUB_MODE` hooks to `publish_core`; in-process publish bypasses the fake `bin/python3` stub.
  - Move all rc-matrix orchestration coverage to `python/test_design_lifecycle.py` via monkeypatch on `design_publish.publish_core`.

## Files to modify/create

### UPDATED: python/design_lifecycle.py

- Add `step5c_core(argv)` and `step5c_main(argv)` near the Step 5b lifecycle functions.
- In `step5c_main`, call `logging_util.quiet_init(argv0="design-step5c.sh")` before `step5c_core`, matching `step_final_summary_main`. This ensures `_emit_final_summary_marked_from_disk`, `emit_kv`, and `REPORT_GATE_SIDECARS_FILE=` reach the orchestrator-visible contract stream under inherited quiet routing.
- Parse the same wrapper flags as the Bash wrapper:
  - `--session-env-path`
  - `--claude-pid`
  - `--plugin-root`
  - `--mode`
  - `--skip-validate`
- Rehydrate the wrapper env with existing helpers (`_parse_common_wrapper_args`, `_rehydrate_wrapper_env`).
- Validate:
  - `CLAUDE_PLUGIN_ROOT`
  - `DESIGN_TMPDIR`
  - `$DESIGN_TMPDIR/.completed/step-5b`
- Preserve `.pause-requested` handling by invoking `design pause-save` before publish work.
- Create `.bg-wait-active` with `STEP=design-step5c` through `_bg_wait_marker_context`.
- Assemble `publish_core` argv from rehydrated env with the same required flags as the current subprocess call in `design-step5c.sh`:
  - `--design-tmpdir "$DESIGN_TMPDIR"`
  - `--issue "$ISSUE_NUMBER"`
  - `--session-id "$SESSION_ID"`
  - `--claude-pid "$CLAUDE_PID"`
  - optional `--repo "$REPO"` when set
  - optional `--skip-validate` when the wrapper flag is set
- Call the publish tail in-process by importing `design_publish` locally and invoking `publish_core(argv)`.
- Capture publish stdout to a temp file, matching the current Bash wrapper behavior.
- Preserve publish rc handling:
  - `0`, `1`, `3`, `4`: parse result rows and continue wrapper handling.
  - `2`: stage `failed-publish-tail`, render final summary, emit markers and sidecar handoff, return `1`.
  - unexpected non-zero, including `5`: same abort path as rc `2`.
- Preserve stale-env avoidance:
  - For rc `1`, `3`, and `4`, ignore the primary `.design-publish-result.env` by using a guaranteed-missing primary input and parsing captured stdout.
- Reuse the Python `design read-result-env` implementation (`read_result_env_main` or an equivalent allowlisted helper). Do not call `scripts/read-result-env.sh`.
- After parsing publish rows, set `os.environ["FINAL_SUMMARY_PATH"]` when the parsed value is non-empty **before** any marker emission. `_emit_final_summary_marked_from_disk` reads `os.environ["FINAL_SUMMARY_PATH"]` when set; skipping this bind can emit markers from a stale/default path after rc `1`/`3`/`4` stdout-authority parsing.
- Write `.completed/step-5c` only when `PLAN_WRITE_OK=true`.
- Write `.completed/step-5c-terminal` in a `finally` path for normal and abort exits after `DESIGN_TMPDIR` is known (including rc `2` and unexpected-rc abort paths). Current Bash exits before `write_step5c_wrapper_sentinel` on publish-tail abort; the port fixes this for orchestrator probe rules.
- Write `.design-step5c-status.env` with:
  - `PLAN_WRITE_OK`
  - `PUBLISH_OK`
  - `STANDALONE_HEAVY_FAILED`
  - `SESSION_ID`
  - `PUBLISH_RC`
  - `PUBLISH_STDOUT_FALLBACK`
  - `CLEANUP_ELIGIBLE`
- Emit the exact machine rows the orchestrator parses:
  - `VALIDATE_STATUS`
  - `VALIDATE_DEFECT_COUNT`
  - `VALIDATE_SKIPPED_COUNT`
  - `VALIDATE_UNSAFE_TOKEN_COUNT`
  - `VALIDATE_LOG_FILE`
  - `FINAL_SUMMARY_PATH`
  - `UPSERT_STATUS`
  - `ARCHITECTURE_SOURCE`
  - `STEP5C_STATUS=validator-defects` for rc `4`
- On rc `0`, `1`, and `3`:
  - Capture `design_summary.render_final_summary_main` stdout to `$DESIGN_TMPDIR/render-final-summary.<outcome>.stdout.log` (same filenames as Bash: `approved` or `failed-plan-write`) via `contextlib.redirect_stdout` or equivalent.
  - Do not forward render stdout to Step 5c contract stream.
  - Emit `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END` from disk via `_emit_final_summary_marked_from_disk` after render.
- On rc `4` (validator defects):
  - Do not call `render_final_summary_main`.
  - Emit `STEP5C_STATUS=validator-defects`.
  - Emit `REPORT_GATE_SIDECARS_FILE=` via `_emit_report_gate_sidecars_from_disk` when sidecars exist.
  - Do not emit final-summary markers.
- On publish-tail abort (rc `2` or unexpected non-zero):
  - Capture `render_final_summary_main` stdout to `$DESIGN_TMPDIR/render-final-summary.failed-publish-tail.stdout.log`.
  - Emit marked summary and sidecar handoff from disk only.
- On all paths that emit sidecars after marked summary (rc `0`, `1`, `3`, abort paths): emit `REPORT_GATE_SIDECARS_FILE=` after marked output, never from uncaptured render stdout.
- Stage publish-tail aborts by calling `stage_terminal_state_core` through `_capture_contract_stream_to_paths` into:
  - `$DESIGN_TMPDIR/design-stage-terminal-state.stdout.log`
  - `$DESIGN_TMPDIR/design-stage-terminal-state.stderr.log`
  - matching the clarify hard-halt pattern (`step0_clarify_hard_halt_main`) and existing `_append_failure` branches on `STAGED=false` vs non-zero rc.
- Append staging warnings through the existing `_append_failure` helper when staging returns `STAGED=false` or fails.

### UPDATED: python/design_publish.py

- Keep the module and `review_provenance` stable.
- Split `publish_main(argv)` into:
  - `publish_core(argv)` callable used by Step 5c in-process
  - the existing CLI wrapper entrypoint `publish_main(argv)` delegating to `publish_core`
- Keep current publish behavior:
  - provenance splice
  - composed-plan validation
  - secret redaction
  - `named-block write --marker plan`
  - diagrams upsert
  - `[DESIGNED]` rename
  - design log publish
  - secret-scrub rotation warning
  - result-env rows
- Preserve publish exit codes:
  - `0`: publish flow completed.
  - `1`: plan block write failed after row emission.
  - `3`: result-env write failed after validation passed, with stdout rows still available.
  - `4`: validator defects after row emission.
  - `5`: usage or unexpected internal failure.
- Add a small result-env write helper so write failures can return `3` without losing stdout fallback rows.
- Preserve rc `4` precedence: when validator defects are detected, return `4` even if the result-env write fails; Step 5c treats that as the rc `4` stdout-authority path (missing-primary + stdout parse), not a generic rc `3` continuation.
- Reserve rc `3` for post-validation result-env write failures on otherwise continuing paths (no validator defects).
- Do not move `review_provenance`.
- Do not delete or rename `python/test_design_publish.py`.

### UPDATED: python/cli.py

- Add the command row:
  - `("design", "step5c"): ("design_lifecycle", "step5c_main")`
- Add `("design", "step5c")` to `_DESIGN_LIFECYCLE_STDOUT_KEYS` so inherited quiet routing does not hide `PUBLISH_RC`, `PLAN_WRITE_OK`, `VALIDATE_*`, final-summary markers, or `REPORT_GATE_SIDECARS_FILE=` from orchestrator-visible stdout.
- Keep the existing row:
  - `("design", "publish"): ("design_publish", "publish_main")`

### UPDATED: skills/design/scripts/design-step5c.sh

- Replace the current Bash body with a thin delegation wrapper.
- Match the existing Step 5b wrapper style:
  - derive `CLAUDE_PLUGIN_ROOT` from the script path when unset
  - export `CLAUDE_PLUGIN_ROOT`
  - `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design step5c "$@"`
- Do not change how `skills/design/SKILL.md` invokes the wrapper.

### UPDATED: skills/design/scripts/design-step5c.md

- Update the purpose to describe the wrapper as a thin delegator.
- Move orchestration invariants to the Python entrypoint description.
- Keep the contract details:
  - `.bg-wait-active`
  - result-env fallback rules
  - final-summary markers
  - sidecar handoff
  - sentinels
  - cleanup eligibility
- Document rc `4` explicitly: no render/markers; emit `STEP5C_STATUS=validator-defects` and `REPORT_GATE_SIDECARS_FILE=` only.
- Document render stdout capture to `render-final-summary.*.stdout.log` before disk-based marker emission.
- Document `finally`-guaranteed `.completed/step-5c-terminal` on abort paths.

### UPDATED: skills/design/scripts/test-design-step5c.sh

- Retarget as thin-wrapper delegation smoke only.
- Change the fake plugin stub so `python3 ... cli.py design step5c` is the observed command.
- Remove reliance on `DESIGN_PUBLISH_STUB_RC` / `DESIGN_PUBLISH_STUB_MODE` driving `design publish` (in-process publish bypasses that stub entirely).
- Remove all rc-matrix cases (rc `0`/`1`/`2`/`4`/`9`, stale-env, marked-summary, render-on-absent-summary, terminal-sentinel on abort).
- Keep minimal coverage:
  - wrapper execs `python/cli.py design step5c` with expected argv passthrough
  - non-zero exit propagates when the Python entrypoint fails preflight

### UPDATED: python/test_design_lifecycle.py

- Add unit tests for `step5c_core`.
- Monkeypatch `design_publish.publish_core` instead of shelling out or stubbing CLI `design publish`.
- Cover:
  - missing `DESIGN_TMPDIR`
  - missing `.completed/step-5b`
  - `.pause-requested` path
  - `.bg-wait-active` creation and cleanup
  - `quiet_init` contract-stream visibility (machine rows reach stdout)
  - `publish_core` argv assembly (`--issue`, `--session-id`, `--claude-pid`, optional `--repo`, `--skip-validate`)
  - rc `0` success path with render capture and marked summary emission
  - rc `0` summary render when `final-summary.md` is absent
  - rc `1` plan-write failure path with `FINAL_SUMMARY_PATH` env binding before markers
  - rc `3` stdout fallback path (post-validation result-env write failure)
  - rc `4` validator-defects path: `STEP5C_STATUS=validator-defects`, sidecars, no markers, no render call
  - rc `4` with stale primary result env: stdout authority over stale file
  - rc `1` with stale primary result env: stdout authority over stale file
  - rc `2` publish-tail abort staging with `_capture_contract_stream_to_paths` log files
  - unexpected rc publish-tail abort staging
  - `.completed/step-5c-terminal` on rc `2`, unexpected-rc abort, and completed paths
  - `.completed/step-5c` gated by `PLAN_WRITE_OK=true`
  - final-summary marker emission without duplicate unmarked render stdout on contract stream
  - `REPORT_GATE_SIDECARS_FILE=` emission after markers (success/abort) and on rc `4` without markers
  - `.design-step5c-status.env` contents
  - cleanup eligibility when `SESSION_ID` is empty, when `PUBLISH_OK=true`, and when `PUBLISH_OK=false`

### UPDATED: python/test_design_publish.py

- Retain existing coverage.
- Add focused tests only for the new callable split and result-env write helper.
- Verify:
  - `review_provenance` remains importable.
  - legacy `publish_main(argv)` still returns the same rc values.
  - result-env write failure returns `3` while stdout rows remain parseable on post-validation paths.
  - validator-defect paths return `4` even when result-env write fails.

### UPDATED: python/test_cli.py

- Existing `test_design_lifecycle_registry_entries_are_machine_stdout` should pass once `("design", "step5c")` is added to `_DESIGN_LIFECYCLE_STDOUT_KEYS` and `_REGISTRY`.
- Add or extend a smoke assertion that `("design", "step5c")` resolves to `design_lifecycle.step5c_main` and is a machine-stdout member.

### UPDATED: python/checks.py

- Add `test-design-step5c` to the direct-target rules for `python/design_lifecycle.py`.
- Keep the existing direct-target rule for `python/design_publish.py` and `python/test_design_publish.py`.
- Keep the existing wrapper direct-target rule for `skills/design/scripts/design-step5c.sh`.

### UPDATED: skills/design/SKILL.md

- Keep the Step 5c wrapper invocation unchanged.
- Update prose that describes the implementation surface:
  - wrapper delegates to `python/cli.py design step5c`
  - Step 5c calls the publish tail in-process
  - `python/cli.py design publish` remains the publish-tail library/legacy verb
- Preserve all orchestrator parsing instructions and output contracts.
- Note rc `4` skips render/markers; sidecar handoff still emits.
- Note `.completed/step-5c-terminal` is written in `finally` on abort paths.

### UPDATED: skills/design/references/flags.md

- Update the Step 5c validation sentence to say validation runs through the Step 5c entrypoint, which calls the publish tail in-process.

### UPDATED: docs/run-logs.md

- Update Step 5c references so run-log docs name `python/cli.py design step5c` as the orchestration entrypoint.
- Keep `design publish` described as the publish-tail implementation surface where relevant.

## Edge cases

- Stale `.design-publish-result.env` must not mask rc `1`, `3`, or `4` stdout rows.
- Parsed `FINAL_SUMMARY_PATH` must be bound into `os.environ` before `_emit_final_summary_marked_from_disk`.
- `render_final_summary_main` stdout must be captured to log files; Step 5c contract stream must not contain unmarked duplicate summary text.
- rc `4` must not call render or emit final-summary markers; it must still emit `STEP5C_STATUS=validator-defects` and `REPORT_GATE_SIDECARS_FILE=` when sidecars exist.
- Validator defects take rc `4` precedence over rc `3` even when result-env write fails.
- `final-summary.md` may be absent before Step 5c renders it on rc `0`/`1`/`3`.
- `REPORT_GATE_SIDECARS_FILE=` must be emitted after marked final-summary output on render paths, and directly on rc `4`.
- A publish-tail abort may happen before normal result parsing; `.completed/step-5c-terminal` must still be written in `finally`.
- `PUBLISH_OK=false` with `PLAN_WRITE_OK=true` must preserve tmpdir cleanup behavior.
- Empty `SESSION_ID` remains cleanup-eligible when `PLAN_WRITE_OK=true` and no standalone-heavy failure exists.
- `review_provenance` imports from `design_summary.py` must keep working.
- Inherited quiet routing must not hide Step 5c machine rows (`_DESIGN_LIFECYCLE_STDOUT_KEYS` membership).
- Wrapper harness `DESIGN_PUBLISH_STUB_*` env vars are obsolete after in-process publish; rc-path coverage belongs in pytest only.

## Failure modes

- If publish returns rc `2` or unexpected non-zero, stage `failed-publish-tail` via `_capture_contract_stream_to_paths`, render a failed summary to log, emit marked summary and sidecar handoff from disk, write `.completed/step-5c-terminal` in `finally`, then return `1`.
- If staging itself fails or reports `STAGED=false`, append a warning to `execution-issues.md` using captured stdout/stderr log files.
- If result-env parsing fails after a continuing publish rc, return `1` and print the existing unreadable-result-env warning.
- If final-summary render fails on a normal continuing path, do not fabricate markers.
- If `.bg-wait-active` setup fails, continue and append a warning, matching existing lifecycle helper behavior.

## Testing strategy

- Run targeted unit tests:
  - `python3 -m pytest python/test_design_lifecycle.py -q -k step5c`
  - `python3 -m pytest python/test_design_publish.py -q`
  - `python3 -m pytest python/test_cli.py -q -k lifecycle_registry`
- Run wrapper harness (thin delegation smoke only):
  - `make test-design-step5c`
- Run direct publish harness:
  - `make test-design-publish`
- Run structure checks:
  - `make test-design-structure`
- Run Python validation because Python files changed:
  - `make py-lint`
  - `make py-test`
- Run full repo lint before completion:
  - `make lint`

## Acceptance

- `skills/design/scripts/design-step5c.sh` is a thin wrapper.
- `python/cli.py design step5c` runs the full Step 5c wrapper orchestration with `quiet_init` and machine-stdout registration.
- Step 5c calls `publish_core` in-process with the same argv the Bash wrapper passed to `design publish`.
- `python/cli.py design publish` still works.
- `review_provenance` remains importable from `python/design_publish.py`.
- Step 5c stdout rows, final-summary markers, sidecar handoff, status env, sentinels, and cleanup eligibility match the existing orchestrator contract.
- rc `4` emits `STEP5C_STATUS=validator-defects` and sidecars without render or markers.
- Render stdout is captured to log files; contract stream emits markers and sidecars from disk only.
- `.completed/step-5c-terminal` is written on success, rc `2`, and unexpected-rc abort paths.
- Wrapper harness covers thin delegation only; rc-matrix coverage lives in `python/test_design_lifecycle.py`.
- No `DESIGN_PUBLISH_STUB_*` seam in `publish_core`.
- Existing publish tests still pass.
- New Step 5c lifecycle tests cover success, validator, plan-write failure, stdout fallback, abort staging, stale-env paths, and abort terminal-sentinel behavior.

diff_added: 800
diff_deleted: 390
mechanical_churn: true
diff_lines: 1190

## Test plan
(no test plan section in plan-file)
