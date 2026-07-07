## Plan

## Approach

Use the accepted narrow fix from the plan-review findings: tighten route-state gap-fill so it cannot seed a stale `REPO` on a fresh explicit-issue run, without breaking resume recovery when `ISSUE_NUMBER` is only persisted in route state.

- In `_bind_step0_route_issue_env`, call `_gap_fill_resume_route_state_values` only when `ISSUE_NUMBER` is absent (`if not env.get("ISSUE_NUMBER"):`), not when either `ISSUE_NUMBER` or `REPO` is missing (current OR guard) and not when both are missing (rejected AND guard).
- Binding explicit `--issue-number` or `POSITIONAL_KIND=issue` still sets `ISSUE_NUMBER` before this guard, so gap-fill is skipped and stale route-state `REPO` cannot leak onto a fresh explicit issue.
- Resume-like paths with `POSITIONAL_KIND=none` and no `ISSUE_NUMBER` still gap-fill from `.design-step0-route-state.env`, even when ambient or wrapper `REPO` is already non-empty.
- Leave `_recover_resume_route_state_values`, `_refresh_resume_source_env`, route-state file format, `_finish_step0_route`, and the existing `step0_route_main` `resolve_repo()` call (`if env.get("ISSUE_NUMBER") and not env.get("REPO")`) unchanged.

## Files to modify/create

### UPDATED: python/larch/design/design_step0.py

Change the gap-fill trigger in `_bind_step0_route_issue_env` (lines 310–311):

- Current behavior: gap-fill runs when `ISSUE_NUMBER` or `REPO` is missing.
- New behavior: gap-fill runs only when `ISSUE_NUMBER` is missing.
- Keep all other Step 0b binding, verbal guard, and route-state recovery helpers unchanged.

### UPDATED: python/tests/design/test_design_lifecycle.py

Add two focused regression tests near the existing Step 0 route tests.

**Test 1 — fresh explicit issue must not inherit stale route-state `REPO`:**

- Create a design tmpdir with `.design-step0-parsed.env` containing `POSITIONAL_KIND=issue` and `POSITIONAL_VALUE=77`.
- Seed `.design-step0-route-state.env` with stale `ISSUE_NUMBER=42` and `REPO=old/repo`.
- Use a source env without `REPO`.
- Pin ambient `REPO` isolation before `step0_route_main`: `monkeypatch.delenv("REPO", raising=False)` (or `monkeypatch.setenv("REPO", "")`) so the test cannot pass because `os.environ["REPO"]` is already populated and `resolve_repo()` is never exercised.
- Monkeypatch `design_step0.resolve_repo` to return `new/repo`.
- Monkeypatch `_read_json_issue` to assert it receives `issue_number="77"` and `repo="new/repo"`.
- Monkeypatch `subprocess.run` for `design route` and `design init-runparams`; assert the route command includes `--issue 77` and `--repo new/repo`.
- Assert the final route-state file contains `ISSUE_NUMBER=77` and `REPO=new/repo`, not the stale values.

**Test 2 — resume must recover `ISSUE_NUMBER` when ambient `REPO` is already set (FINDING_3):**

- Create a design tmpdir with `.design-step0-parsed.env` containing `POSITIONAL_KIND=none`.
- Seed `.design-step0-route-state.env` with `ISSUE_NUMBER=42` only (no `REPO` key).
- Use a source env without `ISSUE_NUMBER`; monkeypatch or set ambient/wrapper `REPO` to a non-empty value (e.g. `ambient/repo`) so `_load_wrapper_env` seeds `REPO` before binding.
- Monkeypatch `subprocess.run` for `design route`; assert the route command includes `--issue 42`.
- Assert gap-fill restored `ISSUE_NUMBER=42` and routing did not invoke `design route` with an empty `--issue`.

## Edge cases

- Fresh explicit positional issue with stale route-state `REPO`: gap-fill skipped after `ISSUE_NUMBER` bind; `resolve_repo()` supplies the current repo when `REPO` is still unset.
- Fresh explicit `--issue-number` follows the same path because `ISSUE_NUMBER` is set before the guard.
- `POSITIONAL_KIND=none` resume with `ISSUE_NUMBER` only in route state and non-empty ambient `REPO`: gap-fill still runs and restores `ISSUE_NUMBER`.
- Verbal positional without an issue must still fail before stale route-state can revive an old issue.
- Pre-set intentional `REPO` in source env on explicit-issue runs remains preserved (`test_step0_route_preserves_pre_set_repo` behavior unchanged).
- Test 1 must clear or blank ambient `REPO` so a pre-populated process environment cannot mask stale route-state leakage or bypass the `resolve_repo()` path under test.

## Failure modes

- If the guard reverts to OR or switches to both-missing AND, either stale route-state `REPO` can leak (OR) or resume `ISSUE_NUMBER` recovery breaks when ambient `REPO` is set (AND).
- If regression tests only assert stdout, they may miss the wrong repo being passed to `gh issue view` or `design route`.
- If Test 1 leaves ambient `REPO` unpinned, the test can pass or fail for the wrong reason when `os.environ["REPO"]` is already set and `resolve_repo()` is skipped.
- If Test 2 leaves `REPO` out of the wrapper/ambient env, it will not exercise the ambient-`REPO` resume path that motivated the ISSUE_NUMBER-only guard.

## Testing strategy

Run only changed-file Python tests:

```bash
python3 -m pytest python/tests/design/test_design_lifecycle.py -q
```

Optionally run the relevant-checks path if available and fast for the branch:

python3 python/cli.py checks run-relevant

## Difficulty

This is workflow state handling in `/design` Step 0b. The code edit is one condition, but wrong gap-fill semantics can route GitHub reads to the wrong remote or drop paused-issue recovery.

confidence: high

## Acceptance

Run only changed-file Python tests:

```bash
python3 -m pytest python/tests/design/test_design_lifecycle.py -q
```

Optionally run the relevant-checks path if available and fast for the branch:

python3 python/cli.py checks run-relevant

review_status: complete
rounds_completed: 2
difficulty: MODERATE
mechanical_churn: false
diff_lines: 97
