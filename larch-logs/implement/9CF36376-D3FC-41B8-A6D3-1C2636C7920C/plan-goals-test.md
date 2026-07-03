## Goal
Implement issue #6115: [IMPLEMENTING] [BUG] /design is no longer outputting final report.

## Implementation Plan
## Plan

## Goal

Ensure published `/design` run logs contain a populated `final-summary.md`, and terminal flows still upsert the `larch:final-summary` tracking comment.

Confidence: medium.

## Files to modify/create

### UPDATED: python/larch/design/design_summary.py

Add one shared internal helper wrapping `render_final_summary_main` for every caller that must guarantee `final-summary.md` is enriched before `design log-publish` copies the design tmpdir. Keep summary content unchanged.

To stay under the repo's `PLR0913` argument-count lint, collapse the helper's inputs into a small frozen request dataclass (`design_tmpdir`, `outcome`, `mode`, `issue_number`, `session_id`, `repo`, `upsert_summary_comment`, stdout log path) instead of a long parameter list.

The helper:
- always runs full post-phase enrichment (never maps to `--pre-publish-only`), so every caller writes the same enriched body Step 5c writes today;
- honors `upsert_summary_comment: bool` on the request object to suppress the tracking-issue `upsert-summary` call inside `render_final_summary_main` for that invocation only;
- before rendering, unlinks any existing file at the target `final-summary.md` path first, so a render failure never leaves stale content behind for `design log-publish` to capture — if the render then fails, no file exists at all, matching today's non-gating warning behavior;
- returns success or failure as a bool without raising to the caller.

Add one narrowly-scoped pause outcome value to `_VALID_OUTCOMES` (for example `"paused"`), so pause-save rendering has a valid outcome token instead of failing validation or falling back to a degraded render.

### UPDATED: python/larch/design/design_log_publish_flow.py

This is the primary fix: centralize the pre-commit render in the one choke point every caller already goes through, instead of duplicating a pre-render call at each of the three call sites below.

Add an `--outcome` argument to the `design log-publish` CLI surface (`log_publish_main`), alongside the existing `--design-tmpdir`, `--run-id`, `--issue`, and `--repo`. Resolve `mode` internally the same way Step 5c does (from `run-params.json` / `source-env.sh`), so callers do not need to thread an extra `--mode` flag through.

Inside the publish flow, call the shared helper (local, function-scope import to avoid a `design_summary` <-> `design_log_publish_flow` / `design_publish` import cycle) with `upsert_summary_comment=False`, positioned after `_capture_design_transcript` succeeds (or is skipped) and immediately before `_copy_tree_redacted`. This guarantees the committed `larch-logs/design/<RUN_ID>/final-summary.md` always contains the enriched body, for every current and future caller of `design log-publish`, without relying on each caller remembering to pre-render.

This function never upserts the tracking-issue comment itself; that stays the responsibility of the callers below, where it is authoritative.

### UPDATED: python/larch/design/design_step5c.py

Delegate `_step5c_render_final_summary` to the shared helper via a local (function-scope) import, matching the lazy-import pattern this function already uses for `render_final_summary_main`.

Preserve current behavior and position: this call still runs after `_step5c_invoke_publish_core` returns (unchanged — this remains the authoritative post-publish point), with `upsert_summary_comment=True`, same stdout log naming, same non-gating failure handling, and the same marked final-summary emit after Step 5c completes. The now-duplicate inline stale-summary unlink block is removed here because the shared helper performs it.

### UPDATED: python/larch/design/design_publish.py

In `_run_log_publish_after_capture` (and its caller in `publish_core`), pass a new `--outcome` value through to the `design log-publish` subprocess call so the centralized render in `design_log_publish_flow.py` has what it needs:

- on the approved path (`PLAN_WRITE_OK=true`), pass `--outcome approved`;
- on plan-block write failure after validation, if `--session-id` is present, attempt `design log-publish` with `--outcome failed-plan-write` so any committed failure log includes the rendered summary; keep the existing fail-closed return code and result-env behavior, writing the result env only after that attempt completes.

No separate pre-render call is needed in this file — the centralized helper call inside `design log-publish` covers it. Do not alter the renderer's cost, token, difficulty, provenance, or review-detail logic.

### UPDATED: python/larch/design/clarify.py

Pass `--outcome cancelled-clarify` (success path) or `--outcome failed-clarify` (publishable failure path) to the existing `design log-publish` call, so the centralized render covers the committed snapshot the same way it does for `design_publish.py`.

Do not upsert the tracking-issue comment before `design log-publish` runs. Instead, after that call returns (success or best-effort failure), call the shared helper directly (local import) with `upsert_summary_comment=True` so clarify has exactly one authoritative post-publish comment update, reusing the already-rendered `final-summary.md`. This keeps clarify's existing cleanup order otherwise unchanged: plan block write, difficulty sync, response post, label removal, then log-publish, then the comment-upsert call, then the `[DESIGNING]` rename gated on `SESSION_ID` non-empty and `PUBLISH_OK=true`.

### UPDATED: python/larch/design/design_pause.py

Pass `--outcome paused` (the new outcome value) to the existing `design log-publish --reason pause` call. No other changes: the centralized render (upsert always `False`) already guarantees the pause snapshot's committed tree has an enriched `final-summary.md`, and pause never touches the terminal tracking-issue comment.

### UPDATED: python/tests/design/test_design_summary.py

Add coverage for the new shared helper and request dataclass: post-phase enrichment always runs regardless of caller; `upsert_summary_comment=False` skips the tracking-issue upsert call; the new pause outcome validates; stale `final-summary.md` is unlinked before every render attempt so a failed render leaves no file behind.

### UPDATED: python/tests/design/test_design_log_publish_flow.py

Add coverage that the publish flow renders through the shared helper (`upsert_summary_comment=False`) after transcript capture and before the tree copy when `--outcome` is supplied, and that the resulting commit includes an enriched `final-summary.md`.

### UPDATED: python/tests/design/test_design_publish.py

Add coverage that `publish_core` passes `--outcome approved` / `--outcome failed-plan-write` to the `design log-publish` call at the right branch, and that the result env is written only after that call completes.

### UPDATED: python/tests/design/test_design_lifecycle.py

Update Step 5c tests only where delegating to the shared helper changes call shape. Keep assertions that Step 5c emits the marked final-summary block from disk, stale summaries are cleared on approved paths (now via the helper), render failures do not emit stale summary markers, and terminal sentinel timing stays unchanged.

### UPDATED: python/tests/design/test_clarify.py

Add order-sensitive clarify-publish tests: `--outcome cancelled-clarify` / `--outcome failed-clarify` reaches the log-publish call; the tracking-comment upsert call happens only after log-publish returns, not before; rename remains gated on `SESSION_ID` and `PUBLISH_OK=true`.

### UPDATED: python/tests/design/test_design_pause.py

Add a pause-save test that the pause log-publish call carries `--outcome paused` and that the resulting committed snapshot has an enriched `final-summary.md` with no tracking-comment upsert attempted.

### MAY_UPDATE: docs/run-logs.md

Update the `/design` `final-summary.md` timing prose only if it still states that render happens after design-log publish. The corrected contract: `design log-publish` always renders an enriched summary internally before copying the design tmpdir, for every caller; Step 5c's and clarify's own follow-up renders remain the points that upsert the tracking-issue comment.

## Approach

1. Add one shared helper in `design_summary.py` (request dataclass, not a long parameter list) that always fully enriches and takes an explicit `upsert_summary_comment` flag; unlink any stale file before rendering.
2. Centralize the fix in `design_log_publish_flow.py`: render (upsert suppressed) once, right before the tree copy, so every current and future `design log-publish` caller gets a correct committed snapshot without its own pre-render plumbing.
3. Each caller (`design_publish.py`, `clarify.py`, `design_pause.py`) only needs to pass the right `--outcome` value through its existing `design log-publish` call.
4. Keep Step 5c's existing post-publish render (now delegated to the shared helper) as the authoritative tracking-comment upsert point for the publish flow; give clarify its own follow-up upsert call after log-publish returns, since clarify has no other terminal render point.
5. Keep `render_final_summary_main` content logic unchanged. Preserve existing return codes and result-env keys where possible.
6. Leave cancellation `Final summary block` paths (`design_terminal.py`) and the `failed-publish-tail` branch's relative ordering untouched — reviewers flagged both as out of scope for this fix across two review rounds; a separate follow-up can address committed logs for those paths if needed.

## Edge cases

- `SESSION_ID` empty: skip log publish as today; no committed snapshot to worry about in that case.
- Render failure inside the centralized helper call: log a warning, continue existing publish behavior, and do not emit stale summary markers (the unlink-before-render step guarantees this).
- Validator defects: keep repair routing unchanged. Do not publish a terminal final summary for repairable validation defects.
- Pause snapshots: render through the centralized path with the new pause outcome; never upsert the terminal tracking comment.

## Failure modes

- If `design_log_publish_flow.py`'s new render call is wired to run after `_copy_tree_redacted` instead of before, the committed snapshot regresses to today's bug. Cover this ordering directly in `test_design_log_publish_flow.py`.
- If clarify's follow-up upsert call is dropped rather than reordered, clarify runs would silently stop updating the tracking comment. Cover this in `test_clarify.py`.
- If pause's outcome value is missing or invalid, pause-save rendering fails or degrades. The new `_VALID_OUTCOMES` entry closes this gap.
- If render failure becomes gating anywhere, `/design` may fail after a valid plan write. Keep it non-gating everywhere.

## Testing strategy

Run the targeted pytest files for the touched modules:
- `python3 -m pytest python/tests/design/test_design_summary.py`
- `python3 -m pytest python/tests/design/test_design_log_publish_flow.py`
- `python3 -m pytest python/tests/design/test_design_publish.py`
- `python3 -m pytest python/tests/design/test_design_lifecycle.py`
- `python3 -m pytest python/tests/design/test_clarify.py`
- `python3 -m pytest python/tests/design/test_design_pause.py`

Per this repo's convention (lint/test only changed files; CI runs the full sweep on push), lint and test scope through `python3 python/cli.py checks run-relevant` rather than a blanket `make py-test` / `make py-lint` sweep.

## Acceptance

- `python3 -m pytest python/tests/design/test_design_summary.py`
- `python3 -m pytest python/tests/design/test_design_log_publish_flow.py`
- `python3 -m pytest python/tests/design/test_design_publish.py`
- `python3 -m pytest python/tests/design/test_design_lifecycle.py`
- `python3 -m pytest python/tests/design/test_clarify.py`
- `python3 -m pytest python/tests/design/test_design_pause.py`
- `python3 python/cli.py checks run-relevant` covers lint/test scoping for changed files.

diff_lines: 430

## Test plan
(no test plan section in plan-file)
