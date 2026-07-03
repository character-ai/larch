## Goal
Implement issue #6089: [IMPLEMENTING] OOS follow-ups from #5976 (review Step 4 log-root, transcript, heatmap, Step 18).

## Implementation Plan
## Plan

## Approach

Implement the approved narrow scope only.

1. **Review Step 4 log root and RUN_ID guard**
   - In `skills/review/SKILL.md`, define `review_log_root="${LARCH_LOG_ROOT:-$REVIEW_TMPDIR/larch-logs}"` before any Step 4 larch-log command.
   - Keep the existing scout-manifest value unchanged by removing only the inner duplicate assignment.
   - Add a Step 4 `RUN_ID` validity guard matching `run_log_batch.validate_run_id_slug`: non-empty, no `..`, no `/`, no `\`, and `^[A-Za-z0-9._-]+$`.
   - Apply that same slug-valid predicate uniformly to both branches: upgrade the existing scout-manifest branch's bare `-n "${RUN_ID:-}"` check to the full slug-valid predicate, not just the new standalone-path guard.
   - Gate review log-phase, standalone transcript capture, and standalone commit on a slug-valid `RUN_ID`.
   - Gate transcript capture on standalone mode, valid `RUN_ID`, and non-empty `LARCH_CLAUDE_SOURCE_FILE`.
   - Do not change nested `/review` ownership. Nested runs still skip transcript capture and commit.

2. **Design publish warning label**
   - Add `warning_step_label: str` to `_TranscriptCaptureContext`.
   - Thread the label through `_append_transcript_warning` (accept the label, or accept `ctx` directly) instead of its current hardcoded `"design Step 5c"` prefix, so every warning it writes — `session-id-drift`, `snapshot-skipped`, `snapshot-write-failed`, `source-env-refresh-failed`, `hoist-failed`, `stale-root-removal-failed` — reflects the caller's actual reason.
   - Update `_remove_root_transcript`, `_fetch_claude_source_snapshot`, `_materialize_claude_source_snapshot`, and `_refresh_design_source_env` to accept and forward the label (or `ctx`) to `_append_transcript_warning`, since these helpers currently take only `design_tmpdir`.
   - Also update the two `_append_transcript_warning` calls made directly inside `_capture_design_transcript` itself (`session-id-drift` and `hoist-failed`) to pass `ctx.warning_step_label`; `ctx` is already in scope there, so these are not covered by the four-helper list above and must be changed separately.
   - Replace the hardcoded `"5c"` in the `run-log capture-transcript` call inside `_capture_design_transcript` with `ctx.warning_step_label`.
   - In `publish_core`, pass `"5c"` for the final publish path.
   - In `log_publish_main`, derive the label from `--reason`: `final` maps to `"5c"`, `pause` maps to `"pause"`.
   - Do not add a new `clarify` reason.

3. **Step 18 duplicate execution-issues flush: investigated, left unchanged this round**
   - Plan review found that `implement_finalize_teardown_main` (via `implement_finalize_main`) validates `finalize-state.sh` through `_validate_finalize_cli_args` *before* calling `teardown()`. If that file is missing, unreadable, or fails validation, the CLI returns early and `finalize._teardown_log_flush` never runs.
   - Step 18's own explicit `execution-issues flush-safety-net` call does not depend on `finalize-state.sh` validity, so today it is the only safety net that covers that failure path.
   - Removing it, as originally planned, would trade a redundant-but-safe flush for a strictly narrower one. The benefit (de-duping an append-only, non-corrupting call) does not justify that regression risk, so `skills/implement/scripts/step-18.sh` and `python/larch/state/finalize.py` are left unchanged this round.

## Files to modify/create

### UPDATED: skills/review/SKILL.md
- Hoist `review_log_root` to the start of Step 4 larch-log work.
- Add prose or shell-pseudocode that validates `RUN_ID` before any review log write, transcript capture, or commit.
- Remove the scout-only `review_log_root` assignment from the embedded scout-manifest block.
- State that all Step 4 review log commands use the hoisted `--log-root "$review_log_root"`.

### UPDATED: python/larch/design/design_publish.py
- Extend `_TranscriptCaptureContext` with `warning_step_label`.
- Thread the label into `_append_transcript_warning` and every helper that calls it (`_remove_root_transcript`, `_fetch_claude_source_snapshot`, `_materialize_claude_source_snapshot`, `_refresh_design_source_env`), replacing the hardcoded `"design Step 5c"` prefix.
- Use `ctx.warning_step_label` for the `run-log capture-transcript --warning-step-label` argument.
- Pass `"5c"` from the existing final publish context creation.

### UPDATED: python/larch/design/design_log_publish_flow.py
- Derive `warning_step_label` from parsed `--reason`.
- Pass that value into `_TranscriptCaptureContext`.
- Keep accepted reasons limited to `final` and `pause`.

### UPDATED: python/tests/design/test_design_publish.py
- Update `_TranscriptCaptureContext` construction in helper tests.
- Add or update assertions that capture argv uses `--warning-step-label 5c` for the default final path, and that snapshot/hoist/drift warning text uses the caller's `warning_step_label`, not a hardcoded `"design Step 5c"` string.

### UPDATED: python/tests/design/test_design_log_publish_flow.py
- Update expected captured context fields.
- Add or update a pause case assertion that `ctx.warning_step_label == "pause"`.

### MAY_UPDATE: scripts/test-review-structure.sh
- Only update if the implementer wants a static pin for the Step 4 review prompt contract.
- Useful pins: hoisted `review_log_root`, RUN_ID validation wording, and standalone capture requiring valid `RUN_ID`.
- Do not create a new review Step 4 regression harness.

## Edge cases

- **`SCOUT_STATUS=na` standalone review**: `review_log_root` is still set, so capture and commit do not stage under a relative `review/<RUN_ID>` path.
- **Invalid `RUN_ID`**: Step 4 skips log writes, capture, and commit instead of passing unsafe or empty values into run-log commands.
- **Nested review**: `SESSION_ENV_PATH` remains the ownership boundary. Parent `/implement` still owns committed logs.
- **Pause publish**: transcript warnings (both the CLI-side `--warning-step-label` and Python-side `_append_transcript_warning` text) say `pause`, not `5c`.
- **Clarify publish**: unchanged. It still defaults to `final` and therefore `5c`, across both warning paths.
- **Bail or stall direct to teardown**: unchanged from current behavior. `finalize._teardown_log_flush` runs when teardown has a run id and `finalize-state.sh` passes validation; Step 18's own flush remains the only coverage when it does not. Neither call site is modified.

## Failure modes

- A too-broad RUN_ID guard could skip valid existing run ids. Match the current slug contract exactly.
- Missing a `_append_transcript_warning` call site while threading `warning_step_label` would leave a partial fix that still hardcodes "design Step 5c" for that path, reproducing this round's Finding #1. Grep every call site in `design_publish.py` before finishing.
- Adding a `clarify` reason would expand scope and alter an approved non-goal.
- A future attempt at the Step 18 de-dup must handle the `finalize-state.sh` validation gate explicitly (move the flush earlier, or add a validation-independent fallback) rather than deleting Step 18's call outright.

## Testing strategy

- Run `python3 -m pytest python/tests/design/test_design_publish.py python/tests/design/test_design_log_publish_flow.py`.
- If `scripts/test-review-structure.sh` changes, run it directly.
- Optionally run `python3 python/cli.py checks run-relevant` after implementation if dependencies are available.

diff_lines: 84

## Test plan
(no test plan section in plan-file)
