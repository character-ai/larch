## Goal
Implement issue #6788: [IMPLEMENTING] Error when running /implement (and likely /design) in client repo with no workflow named "CI".

## Implementation Plan
## Plan

### Approach

- Add a narrow GitHub CLI classifier for the exact missing-workflow shape:
  - `returncode == 1`
  - combined stdout/stderr contains `could not find any workflows named CI`
  - the requested workflow is the configured main-health workflow (`config.MAIN_HEALTH_DEFAULT_WORKFLOW`, currently `CI`)
- Map only that shape to `MAIN_CI_STATUS=skip`.
- Keep these cases unchanged:
  - workflow exists but has no push-to-main runs: `error`
  - malformed JSON: `error`
  - transient auth, rate limit, network, or unknown `gh` failure: `error`
  - PR CI `decide` statuses in `python/larch/implement/ci.py`: unchanged
- Treat `skip` as terminal in wait loops.
- Treat `skip` as "gate not applicable" in `/implement` preflight, pre-merge, and post-merge main-health routing.
- Update prompt prose so `/implement` continues on `skip` but does not describe it as a pass.

**Critical read path change (accepted finding):** `read_main_health()` must call `gh.run_list_filtered_read()` and inspect the raw `CommandResult` before any `_raise_read_failure()` / `ShipError` conversion. The current `gh.run_list_filtered()` wrapper raises on non-zero rc and drops the missing-workflow signature from callers. Classification happens on non-zero rc using `gh._combined(result)` (or a small exported equivalent); JSON parsing runs only after rc `0` or after non-skip error classification.

### Files to modify/create

### UPDATED: python/larch/git/gh.py

- Add a side-effect-free helper (e.g. `is_missing_named_workflow(result: CommandResult, *, workflow: str) -> bool`) that detects the missing-workflow signature from a raw `CommandResult`:
  - require `result.returncode == 1`
  - require `could not find any workflows named {workflow}` in `_combined(result)` (exact phrase gh emits for `--workflow`)
- Keep the helper specific to `gh run list --workflow` failure text; do not broaden to generic rc-1 failures.
- Prefer this typed helper over ad hoc string parsing in callers.
- Optionally factor the rc-0 JSON row parsing from `run_list_filtered()` into a shared private parser (e.g. `_parse_run_list_filtered_rows(result) -> tuple[WorkflowRun, ...]`) so `read_main_health()` and `run_list_filtered()` share one parse path without duplicating row validation.
- Do not change unrelated PR or workflow helpers.

### UPDATED: python/larch/implement/main_health.py

- Add `skip` to `MAIN_HEALTH_STATUSES`.
- Refactor `read_main_health()` to:
  1. Build `gh.WorkflowRunListFilters` from `MainHealthQuery` (same fields as today).
  2. Call `gh.run_list_filtered_read(runner, filters)` and capture the raw `CommandResult`.
  3. On non-zero rc, run the new missing-workflow helper on `_combined(result)` **before** `_raise_read_failure()` or any generic `ShipError` catch.
  4. Return `MainHealthStatus(status="skip", detail=...)` only when the helper matches **and** `query.workflow == config.MAIN_HEALTH_DEFAULT_WORKFLOW`; otherwise preserve existing error handling (raise via `_raise_read_failure` or return bounded `error` detail as today).
  5. On rc `0`, parse JSON from `result.stdout` via the shared parser (or inlined equivalent) and pass runs to `_classify_runs()`.
- Return bounded, single-line skip detail (e.g. configured workflow not present in repo).
- Leave empty run lists in `_classify_runs` as `error` (no change).
- Update `wait_main_health()` so `skip` returns immediately with no retry loop or sleep (add `skip` alongside `pass`/`fail` as terminal).
- Keep `skip` distinct from `pass`.

### UPDATED: python/larch/implement/preflight.py

- Accept `MAIN_CI_STATUS=skip` in success-envelope validation.
- Update the validation error text to list `skip` (`pass`, `fail`, `pending`, `error`, `skip`).
- Preserve the same envelope keys and `main-health.env` shape.

### UPDATED: python/larch/implement/ship.py

- In `_premerge_main_health_gate()`, after health is resolved (including any wait), add an explicit terminal branch **before** the default stall path:
  - `if health.status == "skip": return None`
- In `_postmerge_main_health_gate()`, add an explicit terminal branch alongside `pass` **before** the stall path:
- Keep missing sidecar handling fail-closed.
- Keep `fail`, `pending`, and `error` behavior unchanged.

### UPDATED: skills/implement/SKILL.md

- Add `skip` to the Step 0 / Step 2 main-health routing prose.
- State that `skip` continues because no configured main-health workflow exists in the target repo.
- Do not call it `pass`.
- Keep the allowed preflight envelope keys unchanged.

### UPDATED: skills/implement/references/step2-main-health-fix.md

- Update the "When to load" sentence so the repair reference is not loaded on `skip`.
- Keep the repair flow limited to `MAIN_CI_STATUS=fail`.

### UPDATED: python/tests/git/test_gh.py

- Add coverage for the missing-workflow signature helper (positive match on rc 1 + expected gh text).
- Include negative cases: non-matching gh failure text, rc 1 for a different workflow name, non-rc-1 failures.

### UPDATED: python/tests/implement/test_main_health.py

- Add a test that mocks `run_list_filtered_read` returning rc 1 with `could not find any workflows named CI` and asserts `read_main_health()` returns `skip` (not `error`).
- Add a test that non-matching rc-1 stderr still returns `error`.
- Add a test that rc 0 with `[]` still returns `error` via `_classify_runs`.
- Add a wait-loop test that `skip` is terminal and does not sleep/retry.
- Assert `read_main_health()` calls `run_list_filtered_read` (not `run_list_filtered`) so stderr is available for classification.

### UPDATED: python/tests/implement/test_preflight.py

- Add envelope validation coverage for `MAIN_CI_STATUS=skip`.
- Keep malformed status rejection coverage.

### UPDATED: python/tests/implement/test_ci.py

- Add CLI coverage that `python/cli.py ci main-health` emits `MAIN_CI_STATUS=skip` when `run_list_filtered_read` returns the missing-`CI` workflow signature.

### UPDATED: python/tests/implement/test_ship.py

- Add pre-merge coverage that `skip` returns `None` and continues instead of stalling.
- Add post-merge push-watch coverage that `skip` returns `None` and continues to finalization.
- Preserve existing fail-closed tests for missing `main-health.env`.

### Edge cases

- A repo with no workflow named `CI`: `skip`, continue.
- A repo with a `CI` workflow but no push-to-main runs: `error`, unchanged.
- A repo where `gh` cannot read workflows due to auth, rate limit, network, or malformed output: `error`, unchanged.
- A custom workflow name that is missing: keep current `error` behavior unless it is the configured `CI` main-health workflow.
- A skipped preflight sidecar must still be copied and consumed as normal wire data.

### Failure modes when non-trivial

- If `read_main_health()` keeps calling `run_list_filtered()` instead of `run_list_filtered_read()`, missing-workflow repos still surface `MAIN_CI_STATUS=error`.
- If `skip` is added to the producer but not preflight validation, `/implement` exits with a malformed success envelope.
- If `wait_main_health` does not treat `skip` as terminal, `--wait` can loop until timeout.
- If `_premerge_main_health_gate()` or `_postmerge_main_health_gate()` lack explicit `skip` branches, the new status falls through to `STALLED`.
- If detection is too broad, real `gh` errors could silently disarm a safety gate.
- If `skip` is described as `pass`, run logs become misleading.

### Testing strategy

- Run targeted unit tests:
  - `python -m pytest python/tests/git/test_gh.py -k 'run_list_filtered or workflow or missing'`
  - `python -m pytest python/tests/implement/test_main_health.py`
  - `python -m pytest python/tests/implement/test_preflight.py`
  - `python -m pytest python/tests/implement/test_ci.py -k main_health`
  - `python -m pytest python/tests/implement/test_ship.py -k 'main_health or postmerge_push_watch'`
- Run changed-file lint for edited Python files:
  - `python3 python/cli.py checks run-relevant`
- Do not run broad unrelated harnesses unless changed-file checks request them.

## Acceptance

- Run targeted unit tests:
  - `python -m pytest python/tests/git/test_gh.py -k 'run_list_filtered or workflow or missing'`
  - `python -m pytest python/tests/implement/test_main_health.py`
  - `python -m pytest python/tests/implement/test_preflight.py`
  - `python -m pytest python/tests/implement/test_ci.py -k main_health`
  - `python -m pytest python/tests/implement/test_ship.py -k 'main_health or postmerge_push_watch'`
- Run changed-file lint for edited Python files:
  - `python3 python/cli.py checks run-relevant`
- Do not run broad unrelated harnesses unless changed-file checks request them.

diff_added: 185
diff_deleted: 25
mechanical_churn: false
diff_lines: 210

## Test plan
(no test plan section in plan-file)
