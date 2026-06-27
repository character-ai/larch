## Plan

## Approach

- Apply the resolved CI policy:
  - JSON check buckets `fail` and `pending` block merging.
  - JSON buckets such as `skipping`, `cancelled`, `neutral`, and `unknown` are mergeable.
  - Text fallback blocks `fail`, `pending`, `in_progress`, and `queued`.
  - Text fallback no longer blocks `cancelled` or `skipping`.
- Leave `ci_monitor._classify_checks_json(..., required=True)` unchanged.
  - It already fails closed for required-check verification.
  - The default optional path already treats non-`fail` and non-`pending` buckets as `pass`.
- Add a small `gh.py` diagnostic helper for merge-gate failures.
  - Prefer JSON check rows when available.
  - Report blocking rows as `name=bucket`.
  - Treat empty check rows as a blocking diagnostic.
  - Fall back to text output when JSON is unavailable.
  - Keep the message one line and bounded.
- Add a ship merge-loop guard for repeated unchanged `CI_NOT_READY`.
  - Add a config threshold, default `3`.
  - Track the last CI-not-ready diagnostic and a consecutive count inside the merge loop.
  - Reset the count when the diagnostic changes or when the loop takes a non-merge path.
  - When the count reaches the threshold, write terminal stalled state with step `merge-ci-not-ready`.
  - Return `Outcome.STALLED` with a detail that names the stuck check and bucket.
- Keep the existing review-required branch first.
  - `REVIEW_REQUIRED` must still become `MERGE_RESULT_REVIEW_REQUIRED`.
  - It must not be converted into the new CI-not-ready stall.

## Files to modify/create

### UPDATED: python/larch/git/gh.py

- Change `_pr_checks_json_all_pass` so parseable non-empty JSON rows pass when no row has bucket `fail` or `pending`.
- Keep empty rows as not pass.
- Change `_CHECKS_TEXT_BAD_RE` to remove `cancelled` and `skipping`.
- Add a module-private formatter for blocking check rows.
- Add a public helper such as `pr_checks_not_ready_detail(...) -> str`.
  - Use `pr_checks_read` first.
  - If JSON is parseable:
    - Return `no PR checks returned` for an empty list.
    - Return a compact list for rows whose bucket is `fail` or `pending`.
    - Return a mergeable-policy message if no blockers remain, to handle races.
  - If JSON is not parseable, use `pr_checks_text_read`.
  - For text fallback, return a compact first matching bad status line or a generic unreadable-checks message.
  - Sanitize newlines and cap length before returning.

### UPDATED: python/larch/core/config.py

- Add `SHIP_MERGE_CI_NOT_READY_STALL_THRESHOLD: Final = 3` near `SHIP_MERGE_LOOP_MAX_ITERATIONS`.
- Keep the existing 50-iteration cap as a last-resort guard.

### UPDATED: python/larch/implement/ship.py

- Initialize local CI-not-ready guard state before the `while True` merge loop:
  - `last_ci_not_ready_detail = ""`
  - `ci_not_ready_count = 0`
- Reset that guard when the monitor path is not an immediate merge attempt.
- In the `MERGE_RESULT_CI_NOT_READY` branch:
  - Preserve the existing `REVIEW_REQUIRED` conversion.
  - Otherwise call `gh.pr_checks_not_ready_detail(...)`.
  - Increment the count only when the detail matches the previous detail.
  - Reset to `1` when the detail changes.
  - If the count reaches `config.SHIP_MERGE_CI_NOT_READY_STALL_THRESHOLD`, write terminal state and return `ShipResult(Outcome.STALLED, detail=...)`.
  - Include the stuck diagnostic in the detail.
  - Otherwise keep the current retry behavior: increment `iteration`, write ship state, and continue.

### UPDATED: python/test_gh.py

- Add JSON merge-gate tests:
  - `cancelled`, `skipping`, `neutral`, and `unknown` buckets are accepted.
  - `fail` and `pending` buckets block.
  - Empty JSON rows block.
- Add text fallback tests:
  - `cancelled` and `skipping` no longer block.
  - `in_progress` and `queued` still block.
- Add diagnostic-helper tests:
  - JSON blocker detail includes check name and bucket.
  - Empty JSON returns a clear no-checks diagnostic.
  - Text fallback returns a compact blocking line or generic message.

### UPDATED: python/test_ship.py

- Add a regression test for repeated unchanged `CI_NOT_READY`.
  - Monkeypatch the new threshold to a small value.
  - Make `ci_monitor.monitor` return `action="merge"`.
  - Make `merge.merge_pr` return `MERGE_RESULT_CI_NOT_READY`.
  - Make `gh.pr_review_decision` return a non-review-required value.
  - Make `gh.pr_checks_not_ready_detail` return a stable detail such as `blocking checks: lint=pending`.
  - Assert `Outcome.STALLED`.
  - Assert the result detail includes `lint=pending`.
  - Assert terminal state uses `STALL_STEP=merge-ci-not-ready`.
- Add or extend a test showing a single `CI_NOT_READY` still consumes iteration budget and can later merge.
- If implementing unchanged-detail reset, add a small test where the first diagnostic changes and the guard does not trip early.

### UPDATED: python/test_ci_monitor.py

- Rename or broaden `test_default_optional_json_classifier_unchanged_for_unknown_bucket`.
- Assert the optional classifier remains lenient for `cancelled`, `skipping`, `neutral`, and `unknown`.
- Keep the required-path fail-closed tests unchanged.

## Edge cases

- Empty check rows still block merge.
- Text fallback still treats `queued` and `in_progress` as not ready.
- Required-check verification remains fail-closed.
- Review-required PRs still surface as review-required, not CI stalled.
- A race where the diagnostic helper sees mergeable checks after `merge_pr` returned `CI_NOT_READY` should produce a clear race-like detail and retry until threshold or success.
- Transient `gh` read failures may appear as generic diagnostics, but the unchanged-detail threshold prevents immediate stall.

## Failure modes

- If JSON and text parsing use different bucket policies, the original disagreement can return.
- If the guard does not reset on changed diagnostics, a progressing CI run may stall too early.
- If the diagnostic includes raw multiline check output, state files or JSON output may become hard to parse.
- If `REVIEW_REQUIRED` is checked after the new guard, review-blocked PRs may get the wrong stalled reason.

## Testing strategy

- Run focused tests:
  - `python3 -m pytest python/test_gh.py python/test_ci_monitor.py python/test_ship.py`
- If time permits, run merge-adjacent tests:
  - `python3 -m pytest python/test_merge.py python/test_merge_bash_parity.py`
- Run lint for changed Python files:
  - `make py-lint`

## Acceptance

- Run focused tests:
  - `python3 -m pytest python/test_gh.py python/test_ci_monitor.py python/test_ship.py`
- If time permits, run merge-adjacent tests:
  - `python3 -m pytest python/test_merge.py python/test_merge_bash_parity.py`
- Run lint for changed Python files:
  - `make py-lint`

review_status: panel-failed
rounds_completed: 1
diff_added: 170
diff_deleted: 25
mechanical_churn: false
diff_lines: 195
