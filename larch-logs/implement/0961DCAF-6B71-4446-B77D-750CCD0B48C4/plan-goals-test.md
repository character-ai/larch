## Goal
Implement issue #5976: [IMPLEMENTING] md-to-py-XI: write session-transcript.jsonl in every run so the reference heatmap accrues.

## Implementation Plan
## Plan

## Approach

Implement the minimum wiring needed to ensure new runs publish `session-transcript.jsonl` when they publish run logs.

Treat `approach-synthesis.txt` as `NO_SKETCHES`. Draft from direct repo inspection and the approved outline. Keep the v3 transcript policy unchanged: only sanitized reference `Read` stubs, no file contents, no other tool blocks, and no historical log rewrite.

Centralize `/design` transcript capture at the single shared publish choke point (`design log-publish` / `design_log_publish_flow.log_publish_main`) instead of patching each caller separately, so the pause-save and clarify publish paths both gain capture from one hook and Step 5c does not capture twice. Fix Step 18's `RUN_ID` rehydration to read the production `LARCH_RUN_ID` session-env key. Make standalone `/review` transcript capture durable (committed, not just staged under a tmpdir that Step 5 deletes) and guard it against firing during nested `/review` runs inside `/implement`.

## Files to modify/create

### UPDATED: python/larch/design/design_log_publish_flow.py

Wire transcript capture once, at the shared publish entry point used by Step 5c, clarify, and pause.

- In `log_publish_main`, after argv validation and before `_publish_design_logs` runs, build a `design_publish._TranscriptCaptureContext` from the parsed `--design-tmpdir`, `--run-id` (as `session_id`), `--issue`, `--repo`, `plugin_root` (already resolved from `CLAUDE_PLUGIN_ROOT`), and `claude_pid` read best-effort from the environment (empty string when unavailable; it only feeds a non-blocking `source-env.sh` refresh).
- Call `design_publish._capture_design_transcript(ctx=ctx)`. If it returns `False`, emit `PUBLISH_OK=false` (plus empty `PR_NUMBER`/`PR_URL`) and return 0 without calling `_publish_design_logs`, matching the existing early-return shape already used for invalid repo/run-id/reason in this function.
- If it returns `True` (captured, or a non-blocking skip such as a missing source file), proceed to `_publish_design_logs` unchanged.
- This covers every current and future `design log-publish` caller (Step 5c's `_run_log_publish_after_capture`, `clarify.py`, `design_pause.py`) from one place, so pause-save publishes also carry a transcript.

### UPDATED: python/larch/design/design_publish.py

Remove the now-redundant explicit capture call from the Step 5c publish tail.

- In `_run_log_publish_after_capture`, stop calling `_capture_design_transcript` directly; call `design log-publish` immediately (capture now happens inside `log_publish_main` itself, so Step 5c does not snapshot/hoist the transcript twice).
- Keep `_capture_design_transcript` and `_TranscriptCaptureContext` defined in this module; `design_log_publish_flow.py` imports and calls them.
- Preserve the existing `PUBLISH_OK=false` result-env behavior for the case where the (now inline) capture hygiene failure prevents publish.

### UPDATED: python/tests/design/test_design_log_publish_flow.py

Add coverage for the centralized capture hook.

- Assert `log_publish_main` calls transcript capture before `_publish_design_logs`, using a fake `_capture_design_transcript` that records call order and arguments.
- Assert a capture hygiene failure (`_capture_design_transcript` returns `False`) emits `PUBLISH_OK=false` and skips `_publish_design_logs`.
- Assert a capture skip (returns `True` with no transcript written, e.g. missing source file) still proceeds to `_publish_design_logs`, matching existing Step 5c behavior.
- Cover both `--reason final` (Step 5c) and `--reason pause` call shapes.

### UPDATED: python/tests/design/test_design_publish.py

Adjust Step 5c publish-tail coverage for the moved capture call.

- Update `_run_log_publish_after_capture` assertions so they no longer expect a direct `_capture_design_transcript` call from this function; assert it now calls `design log-publish` directly.
- Keep existing coverage of `PUBLISH_OK` propagation, the secret-scrub warning print, and the recovery-branch path.

### UPDATED: skills/implement/scripts/step-18.sh

Add a Step 18 finalization safety net after token/timing closing marks and before restore/teardown.

- Resolve `RUN_ID` the same way this script already resolves `LARCH_CLAUDE_SOURCE_FILE`: `RUN_ID=$(read_session_key LARCH_RUN_ID "${RUN_ID:-}")`, mirroring `python/larch/state/closeout.py`'s `LARCH_RUN_ID`-first resolution so Step 18 matches production session-env instead of relying on a bare shell `RUN_ID` export.
- If `RUN_ID` is non-empty:
  - call `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" execution-issues flush-safety-net --log-root "$IMPLEMENT_TMPDIR/larch-logs" --run-id "$RUN_ID" --issue-log "$IMPLEMENT_TMPDIR/execution-issues.md"` as already documented in `step-18.md`.
  - if `LARCH_CLAUDE_SOURCE_FILE` is non-empty, call `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" run-log capture-transcript --source-file "$LARCH_CLAUDE_SOURCE_FILE" --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --defer-commit true --execution-issues-log "$IMPLEMENT_TMPDIR/execution-issues.md" --warning-step-label "18"`.
- Relay any `SESSION_TRANSCRIPT_STATUS=` line to stdout.
- Keep both calls best-effort. They must not block teardown.
- Do not invoke git commit here. Step 18 only stages batches under the tmpdir log root. Existing publishing paths decide whether logs are committed.
- Preserve ordering: token/timing marks, safety nets, restore-finalize-state, clear pointer, teardown.

### UPDATED: skills/implement/scripts/step-18.md

Update the Step 18 helper docs.

- State that Step 18 resolves `RUN_ID` via `read_session_key LARCH_RUN_ID`, matching production session-env, before running either safety net.
- State that Step 18 runs both safety nets when `RUN_ID` is available:
  - `execution-issues flush-safety-net`
  - `run-log capture-transcript`
- State that transcript capture is best-effort and uses `--defer-commit true`.
- State that Step 7a remains the primary green-path capture point.
- State that Step 18 covers bail/stall paths that reach finalization before Step 7a.

### UPDATED: skills/implement/scripts/test-step-18.sh

Extend the offline harness.

- Make `make_impl` write `LARCH_RUN_ID=RUN1` (not bare `RUN_ID=RUN1`) and `LARCH_CLAUDE_SOURCE_FILE=source.jsonl` into `session-env.sh`, matching production.
- Add fake CLI handling for `run-log capture-transcript`.
- Assert finalize logs `flush-safety-net` and `run-log capture-transcript`, using the `LARCH_RUN_ID` value.
- Assert both safety nets run before restore-finalize-state and teardown.
- Add a case with no `LARCH_RUN_ID` and no `RUN_ID` env that asserts both safety nets are skipped and teardown still runs.

### UPDATED: skills/review/SKILL.md

Wire standalone review transcript capture in Step 4, made durable and guarded against nested runs. Do not route this batch through `review log-phase`: that path delegates to generic `run-log write`, `session-transcript` has sanitizer `none` in `run_log_batch.py`, and the existing `RUN_ID` log-phase block runs even for nested `/review` inside `/implement` — so a log-phase allowlist entry would both bypass the capture-transcript renderer policy and evade the nested guard below. The only transcript writer is the guarded `run-log capture-transcript` call.

- Guard the new capture and commit calls on `[[ -z "${SESSION_ENV_PATH:-}" ]]` (the existing nested-review marker) so they never fire inside `/implement`-nested review; document that nested review log ownership is unchanged.
- In Step 0, when `LARCH_CLAUDE_SOURCE_FILE` is empty and `LARCH_TOKEN_SESSION_ID` is non-empty, mirror `design_publish._materialize_claude_source_snapshot`/`_fetch_claude_source_snapshot`: run `token claude-source` with `LARCH_TOKEN_SESSION_ID` exported, require the returned `SESSION_UUID` to match it, and only then write `$REVIEW_TMPDIR/claude-source.env` and bind `LARCH_CLAUDE_SOURCE_FILE` to it. Leave both empty and skip capture on a missing session key or a `SESSION_UUID` mismatch; do not bind on raw `SESSION_ID` alone.
- Before cleanup, when not nested and `LARCH_CLAUDE_SOURCE_FILE` is non-empty, call:
  - `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" run-log capture-transcript --source-file "$LARCH_CLAUDE_SOURCE_FILE" --log-root "$review_log_root" --skill review --run-id "$RUN_ID" --defer-commit true --execution-issues-log "$REVIEW_TMPDIR/execution-issues.md" --warning-step-label "4"`
- Relay `SESSION_TRANSCRIPT_STATUS=` like implement/design do.
- After that call, when not nested and `RUN_ID` is non-empty, commit the batches so they survive Step 5 cleanup: call `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" run-log commit --log-root "$review_log_root" --skill review --run-id "$RUN_ID"` best-effort (log a warning on failure; never block Step 5).
- If review has no `execution-issues.md`, pass the path anyway. The capture helper already treats warning append failures as non-fatal.
- Do not add `session-transcript` to the `review log-phase` batch list, and do not change `python/larch/review/review_tally.py`'s batch allowlist.

### UPDATED: python/larch/report/tokens.py

Extend `measure_references_heatmap()` with per-skill transcript coverage.

- Count, for each skill:
  - `runs_observed`
  - `transcript_runs_observed`, using `run_log_corpus.safe_transcript_path(run_dir) is not None`
  - `missing_transcript_runs`
  - `transcript_coverage_ratio`
  - `reference_capture_status`, using `measured` when at least one transcript exists for that skill, else `not-yet-measured`
- Add a coverage section before the existing per-reference heatmap rows, for example:
  - `# transcript_coverage`
  - `skill	runs_observed	transcript_runs_observed	missing_transcript_runs	transcript_coverage_ratio	reference_capture_status`
- Keep the existing per-reference columns stable in their own section, for example:
  - `# reference_heatmap`
  - existing header and rows.
- Update parsing tests to read sectioned TSV output.
- Do not treat a skill with zero reference reads and one transcript as missing data.

### UPDATED: python/tests/report/test_tokens.py

Update and extend heatmap tests.

- Update existing `measure_references_heatmap` assertions for the new sectioned TSV shape.
- Add a case with two design runs, one transcript-bearing and one missing, and assert coverage is `1/2` via fields, not prose.
- Add a review run with a transcript and assert the coverage section includes `review`.
- Keep the symlink transcript test. It should now assert zero transcript coverage for that run and no reference heatmap rows.

### UPDATED: docs/run-logs.md

Document the new committed transcript coverage.

- Add `session-transcript.jsonl` under `larch-logs/review/<RUN_ID>/`.
- Clarify that design, implement, and standalone review runs may include sanitized v3 session transcripts, and that `/design` now captures once at the shared `design log-publish` entry point (covering Step 5c, clarify, and pause).
- State that `token measure-references-heatmap` reports per-skill transcript-bearing runs versus total runs.
- Keep the no-backfill rule explicit.

### MAY_UPDATE: SECURITY.md

Only update if the current text names transcript-bearing skills or committed session-log surfaces in a way that becomes inaccurate after standalone review transcript capture.

- Preserve the #3718/#5871 privacy contract.
- Do not describe new content types. The transcript remains sanitized reference `Read` stubs only.

## Edge cases

- **Missing source file:** `run-log capture-transcript` emits `source-file-missing`; callers continue.
- **Existing transcript:** refresh-mode behavior is unchanged. New Step 18 and review calls use normal deferred capture.
- **Symlink transcript:** heatmap coverage must use `safe_transcript_path`, so symlinks do not count.
- **Design publish without `SESSION_ID`/`RUN_ID`:** clarify and pause already validate this before calling `design log-publish`; the centralized hook only runs once that validation passes.
- **Capture skip (e.g. missing source file):** publish logs without a transcript, for every `design log-publish` caller.
- **Capture hoist/hygiene failure:** block log publish for every caller (`PUBLISH_OK=false`), matching existing Step 5c hygiene.
- **Nested review:** guarded on `SESSION_ENV_PATH`; do not add nested ownership or duplicate review transcripts inside implement logs.
- **Step 18 `RUN_ID` resolution:** falls back through the same key order as `closeout.py` so bail/stall runs with a normal session-env still get captured.

## Failure modes

- **Renderer fails:** capture helper records a warning and returns success status to the orchestrator. Publishing continues without the transcript.
- **Batch write fails:** capture helper emits `write-failed`; Step 18 and review continue, and the centralized design hook only blocks on hoist failures after a successful capture.
- **Step 18 missing tmpdir files:** read helpers fall back to empty values and teardown still runs.
- **Review commit fails:** log a warning; Step 5 cleanup still proceeds. The transcript and other batches may remain non-durable for that run, same as today's pre-existing behavior when `LARCH_LOG_ROOT` is unset.
- **Heatmap mixed old/new logs:** old runs without transcripts lower the coverage ratio instead of being rewritten or hidden.

## Testing strategy

Run only changed-file relevant tests.

- `cd python && pytest tests/design/test_design_log_publish_flow.py tests/design/test_design_publish.py tests/design/test_clarify.py tests/design/test_design_pause.py`
- `bash skills/implement/scripts/test-step-18.sh`
- `cd python && pytest tests/report/test_tokens.py`
- If docs or SECURITY change, run the repo's relevant Markdown checks through `python3 python/cli.py checks run-relevant` when dependencies are available.

## Acceptance

Run only changed-file relevant tests.

- `cd python && pytest tests/design/test_design_log_publish_flow.py tests/design/test_design_publish.py tests/design/test_clarify.py tests/design/test_design_pause.py`
- `bash skills/implement/scripts/test-step-18.sh`
- `cd python && pytest tests/report/test_tokens.py`
- If docs or SECURITY change, run the repo's relevant Markdown checks through `python3 python/cli.py checks run-relevant` when dependencies are available.

diff_added: 280
diff_deleted: 30
mechanical_churn: false
diff_lines: 310

## Test plan
(no test plan section in plan-file)
