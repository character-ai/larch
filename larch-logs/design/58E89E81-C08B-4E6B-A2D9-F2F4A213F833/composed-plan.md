## Plan

## Approach

- Add a new `python/cli.py plan-review normalize-status` verb.
- Keep `skills/design/scripts/design-step3-review.sh` responsible for:
  - argv parsing.
  - session env sourcing.
  - resume-state validation and writes.
  - pause-save ordering.
  - `.bg-wait-active` marker setup.
  - `set -m` process-group launch.
  - background `plan-review run --mode loop`.
  - process-group teardown.
  - EXIT-trap sentinel guarantees.
- Move the post-loop pure logic into Python:
  - safe read of `$DESIGN_TMPDIR/.step3-review-result.env` with stdout fallback (normal mode only).
  - selected-source `WARN`/`ERROR` replay matching `read_result_env_main`.
  - overlay of allowlisted stdout KVs (separate pass).
  - guarded `LOOP_STATUS` → `STEP3_REVIEW_LOOP_STATUS` back-map (only when `STEP3_REVIEW_LOOP_STATUS` is unset).
  - `STEP3_REVIEW_LOOP_STATUS` → `LOOP_STATUS` forward-map (including `panel-init-failed` identity).
  - zero-coverage `panel-failed` → `panel-init-failed` normalization.
  - terminal result-env synthesis for terminal failure statuses.
  - canonical stdout KV envelope emission.
  - escalation evidence recording (stdout captured/suppressed).
  - `postplan-failed` and `panel-init-failed` summary KVs plus exit 1.
- Fold wrapper `--read-result-env` into the same verb with a read mode that uses a separate, Bash-matching simple line scan (not `read_result_env_main`).
- Preserve stdout grammar and ordering byte-for-byte where the wrapper currently emits KVs.
- Route all post-loop `**⚠ Step 3:` markdown warnings through `file=sys.stderr` in Python so machine stdout stays KV-only after Bash thinning.

**WARN/ERROR load contract (normal mode only).** In-process `read_result_env_main` always calls `_replay_warn_error` inside `write_pairs`, so an unsuppressed in-process call would emit machine `WARN=`/`ERROR=` before Stage 1 and again during Stage 2 overlay. Adopt one explicit contract; do **not** reuse `_step5c_safe_publish_env` verbatim:

1. **Quiet env generation.** Call `read_result_env_main` only through a new helper `_step3_read_result_env_quiet(argv) -> tuple[int, Path | None, bool]` that redirects process stdout to `os.devnull` (or equivalent capture discarded on success) for the entire call. The helper writes the quoted temp output file only; it must emit **no** machine `WARN=`/`ERROR=` to the normalizer's real stdout.
2. **Selected-source binding.** Mirror `read_result_env_main` source selection in the helper return value:
   - `selected_source`: the path `read_result_env_main` would read (`primary` when regular; otherwise `fallback_input` when valid).
   - `primary_regular`: `true` only when `.step3-review-result.env` is a regular non-symlink file (same guard as current Bash `_step3_primary_regular`).
3. **Stage 1 — sole selected-source replay.** After quiet load succeeds (or after fallback recovery sets `selected_source` to captured loop stdout), call `_replay_warn_error(selected_source)` **once** on the normalizer's real stdout **before** status mapping and **before** the canonical KV envelope. This is the only selected-source `WARN`/`ERROR` emission path; the quiet `read_result_env_main` call must not leak replay lines.
4. **Stage 2 — stdout overlay (unchanged semantics).** Overlay non-empty allowlisted KVs from captured loop stdout. Replay additional `WARN=` lines from the overlay file **only** when `primary_regular` is true (matching current Bash `design-step3-review.sh` lines 611–614). Stage 2 must not re-run `_replay_warn_error` on the result env file.
5. **Failure recovery.** On `read_result_env_main` failure, return an empty dict, set recover-from-stdout, bind `selected_source` to captured loop stdout when readable, and run Stage 1 `_replay_warn_error` on that fallback only (matching current Bash stderr warning + stdout-only recovery).

## Files to modify/create

### UPDATED: `python/plan_review.py`

Add `normalize_step3_status_main(argv)` and helpers near the existing Step 3 helper surface.

Core helpers:

- Define a single ordered allowlist for the wrapper normalization path:
  - `LOOP_STATUS`
  - `STEP3_REVIEW_LOOP_STATUS`
  - `POSTPLAN_RC`
  - `DEDUP_RC`
  - `PLAN_REVIEW_CONTINUE_REASON`
  - `FINAL_ROUND_NUM`
  - `ACCEPTED_COUNT`
  - `IMPORTANT_ACCEPTED_COUNT`
  - `DEGRADED_PANEL`
  - `DEGRADED_PANEL_WARNING`
  - `INVALID_SLOT_PANEL_WARNING`
  - `ROUNDS_COMPLETED`
  - `TALLY_PLAN_REVIEW_STATUS`
  - `AGGREGATOR_STATUS`
  - `VOTING_TALLY_FILE`
  - `SCOPE_ANCHOR_FILE`
  - `STEP3_REVIEW_CAP_REACHED`
  - `STEP3_REVIEW_ROUND_NUM`
  - `ROUND_NUM`
  - `REVIEW_ROUND_COUNT`
- Add `_step3_read_result_env_quiet(argv) -> tuple[int, Path | None, bool]`:
  - wrap `read_result_env_main(argv)` with stdout fully suppressed for the call duration.
  - on success, return `(0, selected_source_path, primary_regular)`.
  - on failure, return `(rc, None, primary_regular)`.
  - import `_classify_input` / mirror its rules so `selected_source_path` matches what `read_result_env_main` would have chosen (including empty-primary retry to fallback).
- Add `_step3_normalize_load_env(design_tmpdir, stdout_file)` for **normal mode** only:
  - build the same argv as current Bash `_step3_read_result_env` (`--input` = `.step3-review-result.env`, `--fallback-input` = captured loop stdout, Step 3 allowlist, temp output path).
  - call `_step3_read_result_env_quiet(argv)`; on success, load the temp output with `load_bash_quoted_env(path, STEP3_NORMALIZE_ALLOW_KEYS)` (import from `design_lifecycle`); do **not** naively split `KEY=VALUE` lines, because `read_result_env_main` writes values with `_quote_single` and spaced warning strings must round-trip.
  - on quiet-load failure, return an empty dict, set recover-from-stdout, bind `selected_source` to captured loop stdout when readable, and set `primary_regular` from a direct stat of `.step3-review-result.env` (matching current Bash stderr warning).
  - **Stage 1 — selected-source replay:** after env keys are loaded (or recovery path binds fallback stdout), call `_replay_warn_error(selected_source)` **once** on real stdout; this is the sole selected-source `WARN`/`ERROR` path.
  - **Stage 2 — stdout overlay pass:** after env keys are loaded, overlay non-empty allowlisted KVs from captured loop stdout; replay additional `WARN=` lines from the overlay file **only** when `primary_regular` is true.
- Extend `step3_loop_status_to_loop_status` to include `panel-init-failed` in the identity set (maps to `panel-init-failed`, not `fallback="complete"`).
- Add `--read-result-env` mode:
  - **do not** call `read_result_env_main`; stat `.step3-review-result.env` directly, matching `design-step3-review.sh` lines 272–287.
  - regular non-symlink file → `READ_RESULT_ENV_STATUS=ok` plus simple line scan for the seven follow-up keys (`STEP3_REVIEW_LOOP_STATUS`, `LOOP_STATUS`, `ROUNDS_COMPLETED`, `FINAL_ROUND_NUM`, `ACCEPTED_COUNT`, `DEGRADED_PANEL_WARNING`, `INVALID_SLOT_PANEL_WARNING`); naive `key=value` split is correct here because the wrapper never sources this path.
  - missing, symlinked, or non-regular → `READ_RESULT_ENV_STATUS=missing` plus empty follow-up KV values; emit **no** machine `WARN=` lines (unlike `read_result_env_main`, which would print `WARN=read-result-env input is a symlink`).
  - exits 0.
  - does not write markers or dispatch review.
- Add normal mode args:
  - `--design-tmpdir DIR`
  - `--stdout-file PATH`
  - `--loop-rc N`
- In normal mode:
  - load env via `_step3_normalize_load_env` (quoted temp-file path above).
  - if `--loop-rc 2`, emit the same stderr warning and return 1.
  - **status mapping order (mirror Bash lines 623–657):**
    - when `STEP3_REVIEW_LOOP_STATUS` is **unset**, back-map from `LOOP_STATUS` using the current Bash case table (including `zero-findings-degraded-panel` as a no-op that leaves `STEP3_REVIEW_LOOP_STATUS` unset).
    - when still unset and `LOOP_STATUS` is not `zero-findings-degraded-panel`, emit the missing-result stderr warning and default both statuses to `panel-failed`.
    - when `STEP3_REVIEW_LOOP_STATUS` **is set**, **skip** the `LOOP_STATUS` back-map entirely; validate against the allowlisted token set, then forward-map canonical `LOOP_STATUS` from `STEP3_REVIEW_LOOP_STATUS` only (preserving `panel-init-failed` → `panel-init-failed`, `cap-hit` → `cap-reached`, apply-pending statuses → `complete`, etc.). Never rewrite a persisted `STEP3_REVIEW_LOOP_STATUS` from a stale `LOOP_STATUS`.
    - when `STEP3_REVIEW_LOOP_STATUS` remains unset and only `LOOP_STATUS` is present (legacy `zero-findings-degraded-panel` path), validate `LOOP_STATUS` directly without synthesizing `STEP3_REVIEW_LOOP_STATUS`.
  - preserve the special legacy `LOOP_STATUS=zero-findings-degraded-panel` path without emitting `STEP3_REVIEW_LOOP_STATUS`.
  - treat missing or invalid statuses as `panel-failed` with the current stderr warning.
  - compute rounds from `ROUNDS_COMPLETED` or `REVIEW_ROUND_COUNT`, with invalid values as 0.
  - port `_step3_review_zero_round_coverage_missing`.
  - port `_step3_review_write_result_env` as a Python helper that writes `.step3-review-result.env` (including `STEP3_REVIEW_CAP_REACHED=false` on synthesis paths) and calls `step3_loop_write_terminal_step3`.
  - synthesize result env for `panel-failed`, `panel-init-failed`, `tally-error`, `degraded-empty-collector`, and `postplan-failed` only when the primary result env is missing, symlinked, or unreadable.
  - emit the canonical post-loop KV envelope in the current Bash order.
  - call `step3_record_report_evidence` for the same statuses the wrapper currently records, but **capture or redirect its contract stdout** (same pattern as the wrapper's `>/dev/null 2>&1` on `plan-review run --record-report-evidence`); on nonzero return emit only the existing stderr warning (`**⚠ Step 3: failed to record escalation evidence for …**`), never leak `WARN=` KVs before the canonical envelope.
  - emit `SUMMARY_OUTCOME=failed-postplan` and return 1 for `postplan-failed`.
  - emit `SUMMARY_OUTCOME=failed-judge-panel` and return 1 for `panel-init-failed`.
- Emit every post-loop `**⚠ Step 3:` markdown warning with `print(..., file=sys.stderr)` (or equivalent `larch_err` helper pinned to stderr). Never print markdown warnings to the normalizer's real stdout.

Do not change `plan-review run` loop behavior.

### UPDATED: `python/design_lifecycle.py`

- Add `STEP3_REVIEW_CAP_REACHED` to `PHASE_RESULT_ENV_ALLOW_KEYS` so terminal synthesis via `phase_driver_write_result_env` accepts the key the Bash writer already emits (`STEP3_REVIEW_CAP_REACHED=false`).

### UPDATED: `python/cli.py`

Wire the new verb.

- Add `("plan-review", "normalize-status"): ("plan_review", "normalize_step3_status_main")` to `_REGISTRY`.
- Add `("plan-review", "normalize-status")` to `_MACHINE_STDOUT_KEYS`.

### UPDATED: `skills/design/scripts/design-step3-review.sh`

Thin the wrapper.

- Replace the current `--read-result-env` body with:
  - `exec python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review normalize-status --design-tmpdir "$DESIGN_TMPDIR" --read-result-env`
- Keep this branch before pause-save, marker setup, and trap setup.
- After the background loop exits and teardown runs:
  - keep the existing trap replacement and monitor-mode cleanup.
  - call the new normalizer:
    - `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review normalize-status --design-tmpdir "$DESIGN_TMPDIR" --stdout-file "$_plan_review_stdout_file" --loop-rc "$_plan_review_rc"`
  - save its rc.
  - remove the captured stdout file after the call.
  - exit with the normalizer rc.
- Delete the moved Bash-only logic:
  - `_step3_read_result_env`
  - `_safe_step3_env` temp sourcing
  - stdout overlay loop
  - status mapping block
  - zero-coverage normalization block
  - terminal result-env synthesis block
  - canonical KV emission block
  - escalation-evidence call block
  - postplan and panel-init summary exit block
- Keep shell job control and sentinel functions untouched unless needed for delegation cleanup.
- Keep `_step3_review_write_prelaunch_failure`, prelaunch failure handling, and scope-anchor refusal behavior unchanged.
- Keep pre-launch `**⚠ Step 3:` warnings on stderr in Bash (stdout capture failure, monitor-mode unavailable, safe-env allocation failure). Only post-loop status-mapping warnings move to Python.

### UPDATED: `skills/design/scripts/design-step3-review.md`

Update the wrapper contract.

- Say status normalization now lives in `python/cli.py plan-review normalize-status`.
- Say `--read-result-env` delegates to that verb's read mode (direct stat + simple line scan; no `read_result_env_main`).
- Say normal post-loop mode loads the quoted temp env via `load_bash_quoted_env` after a **quiet** in-process `read_result_env_main` call.
- Document the explicit WARN/ERROR contract: quiet `read_result_env_main` (no replay leak) → Stage 1 `_replay_warn_error(selected_source)` once → Stage 2 overlay `WARN=` only when `primary_regular`.
- Document the guarded back-map: `LOOP_STATUS` → `STEP3_REVIEW_LOOP_STATUS` only when the latter is unset.
- Document that post-loop `**⚠ Step 3:` markdown warnings are emitted on stderr by the normalizer, not on machine stdout.
- Keep the process-group launcher and sentinel invariants documented.
- Remove stale prose that says the wrapper itself reads `.step3-review-result.env` through `scripts/read-result-env.sh`.
- Document that loop-end `SUMMARY_OUTCOME` KVs are emitted by the normalizer, not the Bash wrapper.
- Preserve the documented stdout grammar and sentinel contracts.

### UPDATED: `python/test_plan_review.py`

Add focused unit coverage for the new Python normalizer.

Cover:

- `--read-result-env` present:
  - exact `READ_RESULT_ENV_STATUS=ok` grammar.
  - all 7 follow-up KV lines.
  - spaced `DEGRADED_PANEL_WARNING` and `INVALID_SLOT_PANEL_WARNING` values round-trip via simple scan.
- `--read-result-env` missing:
  - exact `READ_RESULT_ENV_STATUS=missing` grammar.
  - empty follow-up KV values.
- `--read-result-env` symlinked result env:
  - `READ_RESULT_ENV_STATUS=missing`.
  - **no** machine `WARN=` on stdout (hook-safe contract).
- normal mode quoted env load:
  - fixture with `_quote_single`-style values (e.g. spaced `DEGRADED_PANEL_WARNING`) loaded via quiet `read_result_env_main` temp output + `load_bash_quoted_env`; assert values survive overlay and envelope emission.
- **quiet-load / no double replay:**
  - during `_step3_read_result_env_quiet`, assert **zero** machine `WARN=`/`ERROR=` lines on stdout.
  - after normalizer completes, assert exactly one selected-source `WARN=` when present in result env (not duplicated before envelope).
  - when `primary_regular` and captured loop stdout also carry a distinct overlay `WARN=`, assert both selected-source and overlay `WARN=` appear once each in envelope order (Stage 1 then Stage 2).
  - when primary result env is missing and loop stdout carries `WARN=`, assert Stage 1 replays from fallback stdout and Stage 2 does **not** add overlay `WARN=`.
- legacy stdout-only `LOOP_STATUS=panel-failed`:
  - back-maps to `STEP3_REVIEW_LOOP_STATUS=panel-failed`.
  - preserves `LOOP_STATUS=panel-failed`.
- legacy `LOOP_STATUS=zero-findings-degraded-panel`:
  - preserves `LOOP_STATUS`.
  - does not emit `STEP3_REVIEW_LOOP_STATUS`.
  - does not emit the missing-result warning.
- persisted `STEP3_REVIEW_LOOP_STATUS` with stale `LOOP_STATUS`:
  - preserves persisted `STEP3_REVIEW_LOOP_STATUS`.
  - forward-maps `LOOP_STATUS` from it.
  - does **not** rewrite `STEP3_REVIEW_LOOP_STATUS` from stale `LOOP_STATUS`.
- `panel-init-failed` persisted in result env:
  - preserves both `STEP3_REVIEW_LOOP_STATUS=panel-init-failed` and `LOOP_STATUS=panel-init-failed` (no fallthrough to `complete`).
- zero-round `panel-failed`:
  - normalizes to `panel-init-failed`.
  - writes synthesized result env with zero rounds and `STEP3_REVIEW_CAP_REACHED=false`.
  - returns 1 and emits `SUMMARY_OUTCOME=failed-judge-panel`.
- launched-round terminal failure without persisted result env:
  - synthesizes `.step3-review-result.env` including `STEP3_REVIEW_CAP_REACHED=false`.
  - writes `.step3-terminal-persisted-this-run`.
  - preserves terminal status.
- `postplan-failed`:
  - emits `SUMMARY_OUTCOME=failed-postplan`.
  - returns 1.
- invalid `STEP3_REVIEW_LOOP_STATUS`:
  - normalizes to `panel-failed`.
  - emits current warning text on stderr.
- stdout-only `WARN=some-warning` with no result env:
  - replays `WARN=some-warning` on machine stdout (Stage 1 selected-source replay from fallback stdout).
- stdout `WARN=` overlay when primary result env is regular:
  - replays overlay `WARN=` from captured loop stdout.
- stdout `WARN=` overlay when primary result env is missing:
  - does **not** replay overlay `WARN=` from captured loop stdout (only Stage 1 selected-source replay applies).
- escalation evidence failure:
  - assert no `WARN=` leaks to stdout before the canonical envelope; stderr warning only.
- **KV-only stdout contract (relocated from wrapper harness):**
  - subprocess normalizer on missing-result and invalid-status fixtures: assert captured stdout contains no `**⚠ Step 3:` lines.
  - assert the same warnings appear on captured stderr when expected.

Use direct CLI subprocess calls where stdout ordering matters.

Add static grep pins (relocated from the wrapper harness):

- `grep -Fq 'SUMMARY_OUTCOME=failed-postplan'` in `python/plan_review.py`.
- `grep -Fq 'SUMMARY_OUTCOME=failed-judge-panel'` in `python/plan_review.py`.
- `grep -Fq 'load_bash_quoted_env'` in `python/plan_review.py` (normal-mode quoted load).
- `grep -Fq '_step3_read_result_env_quiet'` in `python/plan_review.py` (quiet-load contract).
- `grep -Fq 'file=sys.stderr'` in `python/plan_review.py` within `normalize_step3_status_main` (or a dedicated `_step3_normalize_warn_stderr` helper) so post-loop markdown warnings cannot regress to stdout.

### UPDATED: `skills/design/scripts/test-design-step3-review.sh`

Keep the existing end-to-end wrapper coverage, but fix the fake plugin, static pins, and kill-test stub.

**Fake plugin (`make_fake_step3_plugin`) — required fix:**

- Bake the repo root into the generated fake `python/cli.py` at stub creation time (e.g. embed `"$ROOT"` as a string literal for the real CLI path), **or** unconditionally export `LARCH_TEST_REAL_REPO_ROOT="$ROOT"` on every wrapper invocation in this harness.
- Requirement: every non-`plan-review run` verb, including `plan-review normalize-status`, must hit the real repo CLI even when individual test cases do not set `LARCH_TEST_REAL_REPO_ROOT`.
- Ensure `make_fake_step3_plugin` still intercepts only `plan-review run`.
- Remove the stale `ln -sf "$ROOT/scripts/read-result-env.sh"` symlink if nothing in the thinned wrapper references it.

**Kill-helper test custom `cli.py` — required fix:**

- The kill test overwrites `make_fake_step3_plugin`'s stub with a custom `cli.py` (lines 328–350). Extend that override so `plan-review normalize-status` (and any other post-loop verbs the thinned wrapper still calls) forwards to the baked real repo CLI via `LARCH_TEST_REAL_REPO_ROOT` / embedded `"$ROOT"`, same contract as `make_fake_step3_plugin`.
- Do **not** route `plan-review normalize-status` to the generic `HELPER_RC` handler (default 73); that breaks the kill test even when `make_fake_step3_plugin` is correct.
- Preferred shape: keep `plan-review run` interception for the loop stub; delegate all other verbs (including `plan-review normalize-status`) to the real CLI; retain `HELPER_RC` handling only for `session kill-background-processes` and other true helper verbs the kill test exercises.

**Static contract pins — relocate:**

- **Remove** wrapper grep at lines 228–231 (`printf.*\*\*⚠ Step 3` routed to stderr). Post-loop warnings move to Python; this pin would pass vacuously after thinning.
- **Remove** wrapper greps for `SUMMARY_OUTCOME=failed-postplan` and `SUMMARY_OUTCOME=failed-judge-panel` (lines 79–80; those KVs move to Python).
- **Remove** wrapper grep for `**⚠ Step 3: postplan failed` on stdout (lines 76–77); relocate KV-only enforcement to `python/test_plan_review.py` and/or `python/plan_review.py` static pins above.
- **Add** static pin that the wrapper calls `plan-review normalize-status`.
- **Add** static pins (or rely on `python/test_plan_review.py` greps above) that `SUMMARY_OUTCOME=failed-postplan` and `SUMMARY_OUTCOME=failed-judge-panel` live in `python/plan_review.py`.
- **Add** static pin that `python/plan_review.py` routes normalizer markdown warnings to stderr (`file=sys.stderr` near `normalize_step3_status_main`).
- Remove or update static assertions that require direct `scripts/read-result-env.sh` usage in this wrapper.

Keep existing behavioral assertions for:

- missing result env.
- legacy `LOOP_STATUS=panel-failed`.
- synthesized terminal result env.
- legacy `zero-findings-degraded-panel`.
- stale sentinel clearing.
- missing scope anchor.
- zero-round panel failure.
- degraded zero-round panel failure.
- empty round-1 coverage.
- `--read-result-env` grammar (including spaced warning values).
- `INVALID_SLOT_PANEL_WARNING` replay.
- runtime wrapper stdout checks for `SUMMARY_OUTCOME=failed-postplan` / `failed-judge-panel` on terminal failure paths (behavioral, not static wrapper grep).
- kill-helper ordering: loop marker before `session kill-background-processes`, helper failure ignored, `STEP3_REVIEW_LOOP_STATUS=complete` on stdout.

**Add** behavioral case: symlinked `.step3-review-result.env` with `--read-result-env` yields `READ_RESULT_ENV_STATUS=missing`, empty follow-up KVs, and no machine `WARN=` lines.

### UPDATED: `skills/design/scripts/test-step3-orchestrator-fence.sh`

Update static pins that currently require `design-step3-review.sh` to contain `read-result-env.sh`.

- Pin `plan-review normalize-status` instead of `read-result-env.sh`.
- Keep pins for:
  - `STEP3_REVIEW_LOOP_STATUS` emission (via normalizer delegation).
  - `LOOP_STATUS` emission (via normalizer delegation).
  - `--starting-round` forwarding.
- Remove pins requiring loop-end `SUMMARY_OUTCOME` literals inside the Bash wrapper.
- Keep behavior tests that launch the wrapper and inspect stdout.

## Edge cases

- `--read-result-env` must remain pure:
  - no `.bg-wait-active`.
  - no `plan-review/` directory creation.
  - no `.completed/step-3`.
  - no `read_result_env_main` call (symlink must yield `missing`, not `WARN=read-result-env input is a symlink`).
- Normal post-loop mode must call `read_result_env_main` only through `_step3_read_result_env_quiet`; never emit its internal `_replay_warn_error` to real stdout during the call.
- Stage 1 `_replay_warn_error(selected_source)` is the sole selected-source `WARN`/`ERROR` path; Stage 2 overlay `WARN=` runs only when `primary_regular`.
- Normal post-loop mode must load quiet `read_result_env_main` output through `load_bash_quoted_env`, not naive splitting.
- A stale `.step3-review-result.env` without `.step3-terminal-persisted-this-run` must not cause the wrapper trap to mint `.completed/step-3`.
- `zero-findings-degraded-panel` is a legacy `LOOP_STATUS` only. Do not synthesize a `STEP3_REVIEW_LOOP_STATUS`.
- Apply-pending and operator statuses must not synthesize terminal sentinels.
- `panel-failed` with zero reviewer coverage must become `panel-init-failed`.
- `panel-failed` after reviewer coverage must remain `panel-failed`.
- `panel-init-failed` must round-trip through both status fields without collapsing to `complete`.
- When `STEP3_REVIEW_LOOP_STATUS` is already set in the loaded env, never back-map from `LOOP_STATUS`; forward-map only.
- New Python reads in normal mode must reject symlinked result envs via `read_result_env_main` fallback semantics.
- Warnings that are markdown prose must stay on stderr. Machine `WARN=` lines must stay KV-compatible and must not leak from suppressed escalation-evidence calls.
- Kill-test fake `cli.py` must not swallow `plan-review normalize-status`; otherwise wrapper exits non-zero and `STEP3_REVIEW_LOOP_STATUS=complete` never reaches stdout.

## Failure modes

- If the normalizer cannot read either result env or stdout, it must use the current fallback behavior:
  - warn on stderr.
  - treat status as `panel-failed`.
  - possibly normalize to `panel-init-failed` when coverage is zero.
- If `read_result_env_main` is called without stdout suppression, double `WARN=` emission ahead of the canonical envelope can break orchestrator parsing and harness stdout-order contracts.
- If `load_bash_quoted_env` drops quoted warning values because naive parsing was used instead, spaced `DEGRADED_PANEL_WARNING` / `INVALID_SLOT_PANEL_WARNING` values truncate and harness replay tests fail; the quiet-load + `load_bash_quoted_env` pattern prevents this.
- If result-env synthesis fails because `STEP3_REVIEW_CAP_REACHED` is not allowlisted, that is a hard defect; the allowlist fix prevents silent synthesis failure.
- If result-env synthesis fails for other reasons, do not abort before stdout KV emission.
- If escalation evidence recording fails, capture contract stdout, emit the existing stderr warning, and continue without pre-envelope `WARN=` leakage.
- If `plan-review run` exits 2, keep the current wrapper behavior:
  - stderr configuration-error warning.
  - exit 1.
  - no unrelated status rewrite.
- If both `STEP3_REVIEW_LOOP_STATUS` and `LOOP_STATUS` are present but disagree, persisted `STEP3_REVIEW_LOOP_STATUS` wins; stale `LOOP_STATUS` must not rewrite terminal routing.
- If post-loop `**⚠ Step 3:` markdown warnings print to normalizer stdout, orchestrator KV parsing and hook-safe contracts break; the relocated harness pins and pytest guard against this regression.
- If the kill-test stub routes `plan-review normalize-status` to `HELPER_RC`, `make test-design-step3-review` fails even when `make_fake_step3_plugin` is otherwise correct.

## Testing strategy

Run targeted tests first:

- `python3 -m pytest python/test_plan_review.py -q -k "normalize or step3"`
- `make test-design-step3-review`
- `make test-step3-orchestrator-fence`

Then run required repo checks for Python and script changes:

- `make py-lint`
- `make py-test`
- `make lint`

## Acceptance

- `python/cli.py plan-review normalize-status` owns the post-loop status normalization, result-env synthesis, canonical KV envelope, escalation-evidence recording, and the `--read-result-env` read mode.
- `skills/design/scripts/design-step3-review.sh` retains only argv parse, resume-state validation, pause-save, `set -m` monitor setup, the background `plan-review run --mode loop` launch, process-group teardown, EXIT-trap sentinel guarantees, and the two normalizer calls. The wrapper shrinks materially while keeping job control.
- The `.completed/step-3` and `.completed/step-3-terminal` sentinel contracts are unchanged.
- The post-loop stdout KV envelope grammar and ordering stay byte-identical to the pre-refactor wrapper.
- The `--read-result-env` recovery grammar (`READ_RESULT_ENV_STATUS` plus the seven follow-up KVs) is unchanged; a symlinked result env yields `READ_RESULT_ENV_STATUS=missing` with no machine `WARN=` line.
- Terminal exit codes are preserved: `postplan-failed` emits `SUMMARY_OUTCOME=failed-postplan` and exits 1; `panel-init-failed` emits `SUMMARY_OUTCOME=failed-judge-panel` and exits 1.
- `make test-design-step3-review`, `make test-step3-orchestrator-fence`, `python3 -m pytest python/test_plan_review.py`, `make py-lint`, `make py-test`, and `make lint` all pass.

review_status: complete
rounds_completed: 5
diff_lines: 805
