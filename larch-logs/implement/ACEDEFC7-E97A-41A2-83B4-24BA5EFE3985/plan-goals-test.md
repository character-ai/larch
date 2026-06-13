## Goal
Implement issue #4243: [IMPLEMENTING] [BUG] (URGENT) Gantt chart in /design final report (and likely also progress report and also /implement final and progress report) missing all info past reviewers.

## Implementation Plan
## Plan

## Plan

Implement the smallest change that restores missing Gantt bars and label clarity.

- Record Step 3 terminal `postplan-failed` timing with the persisted round start.
- Show in-flight progress Gantt charts for the current round, including mixed completed-plus-active round states.
- Fix first-round implement progress so header-only early returns do not suppress in-flight Gantt output.
- Use Step 5 timing marks as the implement in-flight fallback when `round-start-s` is absent.
- Keep manifest label precedence unchanged.
- Mirror Bash and Python fallback label behavior.
- Add explicit plan-autofix task kinds for Codex and Cursor revision attempts.

## Files to modify/create

### UPDATED: skills/design/scripts/review-design-step3-loop.sh

Add `step3_loop_read_round_start_s()`.

Behavior:

- Read `$DESIGN_TMPDIR/plan-review/round-$round_num/round-start-s`.
- Use it only when it exists and is numeric.
- Fall back to the supplied local `round_start_s`.
- Return an empty string only if both sources are invalid.

Use the helper as the `start_s` argument for the three terminal `postplan-failed` timing records:

- `awaiting-postplan-operator` continue-marker failure.
- `awaiting-post-apply` default failure after `step3_loop_run_post_apply`.
- `awaiting-continuation` failure after `step3_loop_run_continuation`.

Add each timing call only after failure is known and immediately before `step3_loop_emit_envelope postplan-failed`.

Do not record timing for:

- Successful operator continue-marker removal.
- `postplan-operator-required`.
- `main-agent-apply-required`.
- `main-agent-vote-required`.
- `per-round-approval-required`.
- Normal apply-required or vote-required bail-outs.

Rationale:

- Resumed phases reset loop-local `round_start_s`.
- `plan-review/round-N/round-start-s` anchors the chart window to the real review round start.
- This keeps reviewer, revision, and postplan vendor rows inside the same Gantt window.

### UPDATED: scripts/render-review-phase-detail.sh

Update only the embedded label fallback logic.

In `derive.awk`, after suffix stripping and lowercasing, add:

- `aggregator` returns `aggregator`.
- `scout-plan-manifest` and `scout-plan-manifest.*` return `scout`.
- Bare vendor cores `codex`, `cursor`, `claude`, and `claude_sub` return that bare vendor token.

In `label_for`, keep manifest map precedence first.

Then add a kind-priority tier:

- If `derive()` returns a bare vendor token and `kind` is non-empty and not `-`, return `vendor/kind`.
- Example: `codex-output.txt` with kind `codex-plan-autofix` renders `codex/codex-plan-autofix`.
- Example: `cursor-output.txt` with kind `cursor-plan-autofix` renders `cursor/cursor-plan-autofix`.

Only after that, return the non-empty derived value.

Keep the final fallback as `vendor/kind`.

### UPDATED: python/progress_report.py

Refactor label-map loading.

- Keep `_progress_label_map(round_dirs)` for completed rounds.
- Add `_progress_label_map_from_manifests(manifest_paths)` for explicit manifest lists.
- Keep completed charts using existing completed-round manifest behavior.
- Let design in-flight charts use:
  - current round `panel-manifest.ndjson` when present,
  - otherwise `DESIGN_TMPDIR/plan-review-slots.ndjson`.
- Let implement in-flight charts use the current round `panel-manifest.ndjson`.

Mirror Bash label fallback behavior.

- Add `aggregator` fallback.
- Add `scout-plan-manifest` fallback.
- Add bare vendor fallback.
- Ensure bare `codex-output.txt` and `cursor-output.txt` can use task kind before the generic prefix branch.
- Preserve manifest label precedence.
- In `_progress_vendor_rows`, apply the same bare-vendor plus non-empty-kind rule before returning a derived bare vendor label.

Add `_render_inflight_gantt(...)`.

Inputs:

- `round_dir`
- `round_num`
- `timing_ledger`
- label manifest paths
- optional `window_start_s`

Window behavior:

- Prefer `round_dir/round-start-s`.
- Then use supplied `window_start_s`.
- Then fall back to the round directory mtime.
- Use current `time.time()` as `window_end_s`.

Rendering behavior:

- Render only completed vendor rows from the timing ledger.
- Return an empty string when no completed vendor rows overlap.
- Use the same heading and fenced ASCII chart shape as completed charts.
- Cap rows with `PROGRESS_GANTT_ROW_CAP`.

Wire implement Step 5 progress.

- Let `_render_step5` accept the latest Step 5 timing mark start.
- Pass that start from `_render_implement`.
- Use the local current round dir for in-flight status and labels.
- Use `_review_rounds_root(...)` for completed detail.
- If no completed `round-meta.json` exists, return `header` plus the current in-flight chart when present.
- Replace any `_all_round_dirs_inflight(selected_root)` header-only branch with the same header plus in-flight chart behavior.
- Keep skipping `_call_render_phase_detail_script` when no completed round metadata exists.
- If completed rounds exist and the current round lacks `round-meta.json`, append the current in-flight chart after completed detail.
- Do not call `_call_render_phase_detail_script` when no completed round metadata exists.

Wire design Step 3 progress.

- Use `_current_round_dir(design_tmpdir / "plan-review")`.
- If no completed `round-meta.json` exists, return `header` plus in-flight chart when present.
- If completed rounds exist and the current round lacks `round-meta.json`, append the current in-flight chart after completed detail.
- Do not call `_call_render_phase_detail_script` when no completed round metadata exists.

### UPDATED: python/plan_quality.py

In `revise_plan_with_waterfall_main`, add explicit timing task kinds for external plan revision attempts.

- For Codex, append `--timing-task-kind codex-plan-autofix`.
- For Cursor, append `--timing-task-kind cursor-plan-autofix`.
- Do not change the Claude revision path unless existing launcher support already requires it.

Keep existing behavior unchanged for:

- `--feature-file`
- `--plan-file`
- `--scope-files`

### UPDATED: python/test_progress_report.py

Add focused coverage.

Label coverage:

- `_derive_progress_label("aggregator-output.txt", ..., ...) == "aggregator"`.
- `_derive_progress_label("scout-plan-manifest.json.raw", ..., ...) == "scout"`.
- Bare vendor outputs with explicit task kinds produce `vendor/kind`.
- `_progress_vendor_rows` applies the bare-vendor task-kind priority when no manifest mapping exists.
- Manifest mapping still wins over derived labels and task kind labels.

Implement Step 5 first-round in-flight coverage:

- Current round has no `round-meta.json`.
- No completed `round-meta.json` exists anywhere under the selected root.
- `round-start-s` exists.
- `panel-manifest.ndjson` maps output to `tool/slot`.
- Timing ledger has at least one completed vendor row.
- Progress output returns the header plus an in-flight Gantt.
- Assert this path does not return header-only through `_all_round_dirs_inflight(selected_root)`.

Add a Step 5 fallback test:

- Current round has no `round-meta.json`.
- Current round has no `round-start-s`.
- Latest Step 5 timing mark supplies the window start.
- A completed vendor row before the round directory mtime still appears in the chart.

Mixed-state implement coverage:

- Round 1 has `round-meta.json`.
- Round 2 lacks `round-meta.json`.
- Output includes completed detail for round 1.
- Output also appends the round 2 in-flight Gantt.

Design Step 3 in-flight coverage:

- Current round has no `round-meta.json`.
- Root `plan-review-slots.ndjson` maps output to `tool/slot`.
- Timing ledger has at least one completed vendor row.
- Progress output appends an in-flight Gantt.

Mixed-state design coverage:

- Round 1 has `round-meta.json`.
- Round 2 lacks `round-meta.json`.
- Output includes completed detail for round 1.
- Output also appends the round 2 in-flight Gantt.

Absence coverage:

- In-flight charts remain absent when there are no completed vendor rows.
- Header-only output remains valid only when there is no completed detail and no in-flight chart.
- Existing completed-round chart tests still pass.

Use `monkeypatch` for `time.time()` where chart windows must be deterministic.

### UPDATED: python/test_plan_quality.py

Add one revise-waterfall argv regression test.

- Use fake Codex and Cursor launchers that record argv to files.
- Run with `--codex-present true --cursor-present true`.
- Make Codex produce no patch so Cursor is attempted.
- Assert Codex argv contains `--timing-task-kind codex-plan-autofix`.
- Assert Cursor argv contains `--timing-task-kind cursor-plan-autofix`.

Keep fake launchers tolerant of unrelated argv.

### UPDATED: scripts/test-render-review-phase-detail.sh

Extend Gantt label fixtures.

Add vendor timing rows that exercise fallback labels:

- `aggregator-output.txt` renders `aggregator`.
- `scout-plan-manifest.json.raw` renders `scout`.
- `codex-output.txt` with kind `codex-plan-autofix` renders `codex/codex-plan-autofix`.
- `cursor-output.txt` with kind `cursor-plan-autofix` renders `cursor/cursor-plan-autofix`.

Keep existing punctuation-preservation and manifest-map tests.

### UPDATED: skills/design/scripts/test-review-design-step3-loop.sh

Add timing-stub coverage for the three `postplan-failed` paths.

- Create a `record-timing-stub.sh` that appends round, start, and end to a temp file.
- Pass it through `RUN_STEP3_RECORD_TIMING_SH`.
- Seed `plan-review/round-1/round-start-s` with a known epoch.
- Force each targeted failure path:
  - postplan operator continue-marker failure.
  - post-apply hard failure.
  - continuation failure.
- Assert one timing record is written before each targeted `postplan-failed` envelope.
- Assert the recorded round is `1`.
- Assert the recorded start equals the persisted `round-start-s`.
- Assert the recorded end is numeric and greater than or equal to the start.

Avoid broad rewrites of existing loop tests.

## Edge cases

- Missing or unreadable timing ledger: progress report remains header-only or detail-only.
- No completed vendor rows during an in-flight round: omit the chart.
- Missing manifest labels: fall back to derived labels.
- Malformed timing rows: ignore them.
- Missing `round-start-s`: use supplied timing mark start when available, then mtime fallback.
- Root design manifest freshness rules stay unchanged.
- Manifest labels still win when label maps and output basenames disagree.
- First in-flight implement round: render the in-flight chart when rows exist instead of returning header-only.

## Failure modes

- If both `round-start-s` and the timing mark are absent, the in-flight chart may use a wider mtime-based window.
- If a vendor task is still running, it has no completed vendor row yet and will not appear until recorded.
- If a task kind is absent, bare vendor outputs fall back to the bare vendor label.

## Testing strategy

Run targeted tests first:

```bash
python3 -m pytest python/test_progress_report.py python/test_plan_quality.py
bash scripts/test-render-review-phase-detail.sh
bash skills/design/scripts/test-review-design-step3-loop.sh
```

Then run repo-relevant checks:

```bash
bash scripts/relevant-checks.sh
```

diff_added: 278
diff_deleted: 39
diff_lines: 317

## Acceptance

All plan sections (review-design-step3-loop.sh postplan-failed timing with persisted round start, render-review-phase-detail.sh label fallback, progress_report.py in-flight Gantt and label parity, plan_quality.py timing task kinds, and all test updates) are implemented and pass relevant-checks.

diff_lines: 317

## Test plan
(no test plan section in plan-file)
