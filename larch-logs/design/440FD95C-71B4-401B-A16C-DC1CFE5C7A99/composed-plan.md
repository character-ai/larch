## Plan

## Approach

Implement the smallest lifecycle change that closes the stale summary gap, scoped to outcomes proven not to double-publish.

1. Add one shared disk-upsert helper in `design_summary.py` (not `clarify.py`), so clarify, terminal, and step5c can all import it without a circular import.
   - `upsert_final_summary_from_disk(...) -> bool`: validate `final-summary.md` is a regular non-empty file, build the `larch:final-summary` marker, call `tracking-issue upsert-summary --content-file`, and return `True` only on return code `0`.

2. In clarify publish flow, stop re-rendering the final summary after `design log-publish`.
   - Reuse `DESIGN_TMPDIR/final-summary.md`, which `design log-publish` rendered before copying logs, via the shared helper from item 1.
   - Parse `RECOVERY_BRANCH` from the `design log-publish` stdout; treat a non-empty value as publish failure, alongside a missing file, non-zero upsert, or raised helper error.
   - Return `PUBLISH_OK=false` and avoid `CLARIFY_PUBLISH_STATUS=ok` when the follow-up upsert fails or recovery was needed.

3. In terminal final-summary flow, route only cancellation outcomes that never already published through `design log-publish`.
   - Keep paused handling unchanged.
   - Keep approved/non-terminal render behavior unchanged to avoid duplicate log PRs.
   - Route `cancelled-*` outcomes except `cancelled-clarify` through the centralized publish path. `cancelled-clarify` already published via clarify's own log-publish call before this fence runs.
   - For `cancelled-clarify` and `failed-clarify`, when a non-empty `final-summary.md` already exists from clarify's own publish, skip `render_final_summary_main` entirely; only emit readiness markers and report-gate sidecars from that existing file. Fall back to the original local render only when no such file exists.
   - Do not route any other `failed-*` outcome here: `failed-publish-tail` is fixed directly in `design_step5c.py` (see item 4).
   - After centralized publish succeeds, parse `RECOVERY_BRANCH` the same way as clarify and treat a non-empty value as failure. On a clean success, call the shared disk-upsert helper; only emit readiness markers, sidecars, and touch `.completed/step-final-summary` when that upsert also succeeds. On any failure (publish, recovery, or upsert), append an execution issue and return non-zero without touching the sentinel.

4. In `design_step5c.py`'s catastrophic-publish-failure branch, the live source of `failed-publish-tail`, attempt centralized publish before falling back to today's local render, but only when no prior publish attempt already ran this session.
   - First check the captured publish stdout/result-env for existing `PUBLISH_OK`, `PR_URL`, or `RECOVERY_BRANCH` evidence; if any are already present, `design log-publish` already ran, so skip the centralized retry and go straight to today's local-render fallback.
   - Otherwise call the centralized publish helper from item 3 with `--outcome failed-publish-tail`, gating on `PUBLISH_OK` and `RECOVERY_BRANCH` the same way.
   - On a clean publish success, call the shared disk-upsert helper; only treat the attempt as successful, and only skip the local-render fallback, when that upsert also succeeds.
   - On any failure (skip condition, publish failure, recovery, or upsert failure), fall back to today's existing `_step5c_render_final_summary` local render so this rare path never regresses to no summary at all.

5. Fix the actual dry-run gap so the new ordering test can pass against production code.
   - In `design_log_publish_flow.py`'s `--dry-run` branch, call `_render_final_summary_before_copy` before returning `PUBLISH_OK=true`, with no real git/gh side effects.

6. Add targeted tests for all review-flagged gaps.
   - Cover the shared disk-upsert helper's placement (imported by clarify, terminal, and step5c with no circular import) and its fail-closed contract.
   - Cover clarify stale-comment prevention, failure signaling, and the `RECOVERY_BRANCH` check.
   - Cover a non-`cancelled-clarify` outcome using centralized log publish, `cancelled-clarify`/`failed-clarify` skipping re-render when `final-summary.md` already exists, and confirm no outcome triggers a second `design log-publish` call for the same session.
   - Cover `design_step5c.py`'s `failed-publish-tail` retry-then-fallback behavior, including skipping the retry when a prior publish attempt already left evidence.
   - Cover dry-run render ordering against the fixed production branch.
   - Cover real non-empty `SESSION_ID` label-remove failure.
   - Assert pushed run-log summary content, not only file presence.
   - Fix the integration test `PATH` so it uses the hermetic `gh` stub.

## Files to modify/create

### UPDATED: python/larch/design/design_summary.py

Add one shared, neutral helper so clarify, terminal, and step5c can each call it without importing from one another.

- Add `upsert_final_summary_from_disk(*, design_tmpdir, env, issue, session_id, repo_args, ...) -> bool` near the existing `tracking-issue upsert-summary` call in `render_final_summary_main`.
- Validate `design_tmpdir / "final-summary.md"` (or a caller-supplied path) is a regular non-empty file.
- Build marker as `<!-- larch:final-summary v1 runid={session_id} -->`.
- Call `tracking-issue upsert-summary --issue --marker --content-file <path>` (plus `--repo` when set).
- Return `True` only on return code `0`.
- `design_summary.py` does not import `clarify`, `design_terminal`, or `design_lifecycle`, so this stays free of circular imports.

### UPDATED: python/larch/design/clarify.py

Replace `_render_clarify_final_summary` with a call to the shared `design_summary.upsert_final_summary_from_disk` helper. Do not define a clarify-local copy of the disk-upsert logic.

Update `_publish_clarify_log_and_summary`:

- Keep `design log-publish` first.
- Parse `RECOVERY_BRANCH` from its stdout alongside `PUBLISH_OK`; treat any non-empty `RECOVERY_BRANCH` as publish failure (no rename, a failure status such as `log-publish-recovery`), even when `PUBLISH_OK=true`.
- If log publish fails or reports recovery, return `"false"` as today.
- If log publish succeeds cleanly, call `design_summary.upsert_final_summary_from_disk`.
- Return `"false"` when disk upsert fails; append a clarify failure.
- Do not call `render_final_summary_for_request` from clarify.

Update publish status rows:

- On happy path, set `CLARIFY_PUBLISH_STATUS=ok` only when `publish_ok == "true"` and no recovery was reported.
- If the follow-up upsert fails after log publish succeeds, return a failure status such as `summary-upsert-failed`, with `PUBLISH_OK=false`.
- Keep comment-post and label-remove failure statuses, but ensure their `PUBLISH_OK` reflects the final upsert result.

### UPDATED: python/larch/design/design_terminal.py

Add a small helper for terminal publish, likely near `step_final_summary_core`.

- `_is_terminal_publish_outcome(outcome: str) -> bool`: `outcome.startswith("cancelled-") and outcome != "cancelled-clarify"`. Do not match any `failed-*` outcome: `failed-clarify` already publishes via clarify, and `failed-publish-tail` is fixed directly in `design_step5c.py` (see that file's entry).
- `_publish_terminal_final_summary(...) -> tuple[int, bool]`:
  - Call `design_log_publish_flow.log_publish_main` in process, or invoke the existing CLI through the standard helper.
  - Pass `--design-tmpdir`, `--run-id`, `--issue`, `--outcome`, and optional `--repo`.
  - Capture stdout/stderr to `design-log-publish.terminal.stdout.log` and `design-log-publish.terminal.stderr.log`.
  - Parse `PUBLISH_OK` and `RECOVERY_BRANCH`; treat any non-empty `RECOVERY_BRANCH` as failure even when `PUBLISH_OK=true`.
  - Return success only when return code is `0`, `PUBLISH_OK=true`, and `RECOVERY_BRANCH` is empty.
  - Reused by `design_step5c.py`'s `failed-publish-tail` branch (see that file's entry).

Update `step_final_summary_core`:

- Preserve the pause early return.
- Inside the background marker context:
  - For `cancelled-clarify` and `failed-clarify`: when `final-summary.md` already exists and is non-empty (clarify already published and upserted it), skip `render_final_summary_main` and only run `_emit_final_summary_marked_from_disk` plus `_emit_report_gate_sidecars_from_disk` from that file. Fall back to today's local render only when the file is missing or empty.
  - If outcome is a terminal publish outcome (narrowed predicate above) and `SESSION_ID` is present, call the centralized publish helper instead of local `render_final_summary_main`.
  - After a successful, non-recovery centralized publish, call `design_summary.upsert_final_summary_from_disk`. Only when that upsert also succeeds, emit `_emit_final_summary_marked_from_disk` + `_emit_report_gate_sidecars_from_disk` and touch `.completed/step-final-summary`.
  - If `SESSION_ID` is missing, keep local render or fail with a clear execution issue.
  - If centralized publish or the follow-up disk upsert fails, append an execution issue and return non-zero without touching `.completed/step-final-summary`.
- Keep approved and paused outcomes on the existing local render path unchanged.

### UPDATED: python/larch/design/design_step5c.py

Fix the live `failed-publish-tail` source directly instead of relying on `design_terminal.py` alone.

In `step5c_core`'s branch where `_step5c_invoke_publish_core` returns `publish_rc == 2` or a value outside `{0, 1, 3, 4}` (today's early-abort path before `_step5c_render_final_summary`):

- First check the captured publish stdout/result-env for existing `PUBLISH_OK`, `PR_URL`, or `RECOVERY_BRANCH` evidence. If any are already present, `design log-publish` already ran this session: skip the centralized retry and go straight to today's local-render fallback.
- Otherwise attempt the centralized publish helper from `design_terminal.py` with `--outcome failed-publish-tail`, gating on `PUBLISH_OK` and `RECOVERY_BRANCH` the same way that helper does.
- On a clean publish success, call `design_summary.upsert_final_summary_from_disk`; only treat the attempt as successful, and only skip the local-render fallback, when that upsert also succeeds.
- On any failure (skip condition, publish failure, recovery, or upsert failure), fall back to today's existing `_step5c_render_final_summary` local render so this rare path never regresses.
- Add matching lifecycle test coverage in `python/tests/design/test_design_lifecycle.py` that exercises `step5c_core`, not `step_final_summary_core`, for `failed-publish-tail`.

### UPDATED: python/larch/design/design_log_publish_flow.py

Fix the production dry-run branch so the new ordering test is meaningful.

- In `log_publish_main`'s `--dry-run` branch, call `_render_final_summary_before_copy` (same call as the non-dry-run path) before emitting `PUBLISH_OK=true`, keeping every other dry-run side effect (no git/gh calls) unchanged.

### UPDATED: python/tests/design/test_clarify.py

Update existing clarify publish tests:

- `test_design_clarify_publish_happy_path` should no longer monkeypatch `_render_clarify_final_summary`.
- Seed `final-summary.md` before the log-publish response.
- Expect a `tracking-issue upsert-summary` call after `design log-publish` and before `tracking-issue rename`, resolving to `design_summary.upsert_final_summary_from_disk` rather than a clarify-local copy.
- Assert the upsert uses `--content-file <tmpdir>/final-summary.md` and the `larch:final-summary` marker with the run id.

Add or update failure coverage:

- A test where log publish returns `PUBLISH_OK=true`, but the summary upsert returns non-zero.
  - Expected: `PUBLISH_OK=false`.
  - Expected: `CLARIFY_PUBLISH_STATUS` is not `ok`.
  - Expected: no rename call.
- A test where `final-summary.md` is missing after log publish succeeds.
  - Expected: same failure shape.
- A test where `design log-publish` reports `PUBLISH_OK=true` with a non-empty `RECOVERY_BRANCH`.
  - Expected: `PUBLISH_OK=false`, no rename, a failure status distinct from `ok`.
- A non-empty `SESSION_ID` label-remove failure test.
  - Expected: `design log-publish --outcome failed-clarify`.
  - Expected: disk summary upsert runs from `final-summary.md`.
  - Expected: `CLARIFY_PUBLISH_STATUS=label-remove-failed`.
  - Expected: `PUBLISH_OK=true` only when the upsert succeeds.

Remove or rewrite tests that assert clarify calls `_render_clarify_final_summary`. Keep mode-resolution tests only if the helper remains used elsewhere; otherwise delete them as stale behavior.

### UPDATED: python/tests/design/test_design_lifecycle.py

Add terminal publish tests around `step_final_summary_core`, narrowed to the corrected scope, plus `step5c_core` coverage for the new `failed-publish-tail` behavior.

Suggested tests:

- A non-`cancelled-clarify` cancelled outcome (e.g. `cancelled-outline`) uses centralized log publish.
  - Seed a session env with `SESSION_ID`, `ISSUE_NUMBER`, `REPO`, and `SUMMARY_OUTCOME=cancelled-outline`.
  - Monkeypatch `design_log_publish_flow.log_publish_main` or the chosen helper.
  - Have it write `final-summary.md` and emit `PUBLISH_OK=true`.
  - Assert local `render_final_summary_main` is not called, and `design_summary.upsert_final_summary_from_disk` is called.
  - Assert `.completed/step-final-summary` is touched and readiness markers are emitted.
- `cancelled-clarify` does not trigger a second centralized publish.
  - Seed an existing non-empty `final-summary.md` (as clarify would have left it).
  - Monkeypatch the centralized publish helper to fail the test if called; monkeypatch `render_final_summary_main` to fail the test if called.
  - Assert `step_final_summary_core` emits readiness markers and sidecars directly from the existing file.
- Centralized publish failure, recovery, or upsert failure (for an eligible cancelled outcome) does not mark completion.
  - Cover each of: `PUBLISH_OK=false`, non-empty `RECOVERY_BRANCH`, and a failing disk-upsert after a clean publish.
  - Assert no `.completed/step-final-summary` in any case.
  - Assert an execution issue or stderr diagnostic records the failure.
- Approved outcome stays local (existing coverage; keep as a regression guard).
- `step5c_core`'s `failed-publish-tail` branch tries centralized publish first when no prior publish evidence exists.
  - Force `_step5c_invoke_publish_core` to return an out-of-range code with no `PUBLISH_OK`/`PR_URL`/`RECOVERY_BRANCH` in captured output.
  - Monkeypatch the centralized publish helper and the disk-upsert helper to succeed; assert both are called with `--outcome failed-publish-tail`.
- `step5c_core` skips the retry when prior publish evidence already exists.
  - Force the same out-of-range code, but seed captured output with `PUBLISH_OK=false` (or `RECOVERY_BRANCH`) from the earlier attempt.
  - Assert the centralized publish helper is never called and the existing `_step5c_render_final_summary` fallback runs.
- `step5c_core`'s `failed-publish-tail` branch falls back to local render when centralized publish or the disk upsert also fails.
  - Same forced failure as the first `step5c_core` test, but the centralized publish helper (or the disk-upsert helper) also fails.
  - Assert the existing `_step5c_render_final_summary` fallback still runs and still produces a `final-summary.md`.

### UPDATED: python/tests/design/test_design_log_publish_flow.py

Close the log-publish test gaps.

- Extend `test_log_publish_dry_run_success` now that the production dry-run branch calls `_render_final_summary_before_copy`:
  - Assert `_render_final_summary_before_copy` is called before dry-run success returns.
  - Keep no real publish side effects.
- Update `test_log_publish_commits_pushes_and_opens_pr`:
  - After asserting `final-summary.md` exists in the pushed branch, read the blob.
  - Assert it does not contain stale sentinel content.
  - Assert it contains an enriched marker such as `<!-- larch:run-summary v=1 -->` or another stable enriched-summary token.
- Fix `test_log_publish_commits_enriched_final_summary_without_helper_upsert`:
  - Prepend `bin_dir` to `PATH` with `monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ.get('PATH', '')}")`.
  - This forces the hermetic `gh` stub and avoids host `gh`.
- Assert the dry-run-rendered `final-summary.md` content is enriched enough to catch render-before-copy regressions.

## Edge cases

- `design log-publish` can return exit `0` with `PUBLISH_OK=false`; parse the KV, not only the return code.
- A successful log publish may still leave no local `final-summary.md` if render failed before copy. Treat that as clarify follow-up failure.
- `RECOVERY_BRANCH` means logs were pushed incompletely. Treat it as failure everywhere a centralized publish result is gated, not only in clarify.
- Outcomes that already published logs earlier in the same run (`cancelled-clarify`, `failed-clarify`) must never be re-routed through centralized publish; doing so can collide with an existing `larch-logs/design-{run_id}` branch.
- A prior in-session `design log-publish` attempt, evidenced by `PUBLISH_OK`, `PR_URL`, or `RECOVERY_BRANCH` already present in captured output, must block any later centralized retry for the same run.
- Empty or missing `SESSION_ID` should not attempt committed log publish.
- Paused outcomes remain delegated to pause save and are out of scope.

## Failure modes

- Tracking-comment upsert fails after logs commit: surface failure and prevent rename or completion, everywhere the disk-upsert helper is called.
- Terminal or step5c log publish fails: do not touch `.completed/step-final-summary`; leave logs for diagnosis.
- Host `gh` leaks into tests: fix `PATH` setup in affected tests.
- Duplicate summary rendering could reintroduce drift: tests should assert clarify, terminal, and step5c all read `final-summary.md` through the shared helper, not a re-render.
- A too-broad terminal-outcome predicate double-publishes and can fail a second `git worktree add` on an existing branch: keep the predicate scoped to outcomes that never already called `design log-publish` in the same run, and gate step5c's retry on the absence of prior publish evidence.
- A circular import between `clarify.py` and `design_terminal.py`/`design_step5c.py`: keep the shared disk-upsert helper in `design_summary.py`, which imports none of those modules.

## Testing strategy

Run focused Python tests:

```bash
python3 -m pytest python/tests/design/test_clarify.py
python3 -m pytest python/tests/design/test_design_lifecycle.py
python3 -m pytest python/tests/design/test_design_log_publish_flow.py
```

Then run relevant checks if dependencies are present:

python3 python/cli.py checks run-relevant

## Difficulty and confidence

This is HARD.

Confidence: medium. The required behavior is clear and now scoped to outcomes proven not to double-publish, but the change still touches publish lifecycle, tracking comments, three distinct terminal/failure code paths, and run-log PR creation.

## Acceptance

Run focused Python tests:

```bash
python3 -m pytest python/tests/design/test_clarify.py
python3 -m pytest python/tests/design/test_design_lifecycle.py
python3 -m pytest python/tests/design/test_design_log_publish_flow.py
```

Then run relevant checks if dependencies are present:

python3 python/cli.py checks run-relevant

review_status: cap-hit
rounds_completed: 2
difficulty: HARD
diff_lines: 540
