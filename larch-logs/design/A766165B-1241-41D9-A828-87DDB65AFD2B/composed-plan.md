## Plan

Plan: make CI agentic-fix fail closed on stale/passive wait and later-cycle non-health failures, trim dead in-process CI waterfall code, add forbidden-path conflict guard, clarify conflict docs, and replace critical skipped coverage with stubbed tests only.

### Approach

- Treat `NO_SKETCHES` as binding. Draft from code inspection, not planning-panel agreement.
- Keep normal CI fixing on the delegated agentic path.
- Keep pending rebase retry on the existing push-only `run_ci_fix` path.
- Fail closed when the delegated fixer cannot trust CI wait output.
- Add only stubbed tests. Do not add real LLM calls in CI.

### Files to modify/create

#### UPDATED: python/ci_agentic_fix.py

- In `_run_cycle`, change non-health launcher failure routing:
  - On `cycle == 1`, keep `first-fixer-non-health`.
  - On `cycle > 1`, return `waterfall-failed` with the same detail.
  - This lets the delegate continue until the cycle cap instead of surfacing a terminal first-cycle-only status later.
- In `_run_cycle`, change passive CI wait failure handling:
  - If `_wait_for_ci` returns `wait_err`, keep writing the push checkpoint for recovery context.
  - Return `ci-fix-exhausted` instead of `pushed`.
  - Set `next_run_id=None` on every fail-closed terminal return.
  - Do not return `next_run_id=run_id` on wait errors.
- Handle `ACTION=bail` and failure-shaped wait output immediately after the `wait_err` check and before rebase/behind/pass/next_run branches:
  - If `wait.get("ACTION") == "bail"`, return `ci-fix-exhausted` with `BAIL_REASON` or a stable fallback detail.
  - If `wait.get("ACTION")` is not in any expected success/rebase set and no `FAILED_RUN_ID` is present, return `ci-fix-exhausted` to avoid continuing with a stale run_id.
  - All fail-closed returns must set tuple element 6 (`next_run_id`) to `None`.
- Keep `_wait_for_ci` parsing small.
  - Leave `ACTION=bail` parse-valid and handle the fail-closed logic in `_run_cycle`.

#### UPDATED: python/ci_monitor.py

- Trim `run_ci_fix` to the pending push-only path.
  - Keep the `ci_fix_rebase_pending=True` branch.
  - Remove the dead normal waterfall body that captured baselines, launched vendor tiers, verified, staged, and pushed.
  - For `ci_fix_rebase_pending=False`, return a defensive `FixResult(status="waterfall-failed", detail="run_ci_fix: non-pending calls not supported")` so callers fail closed.
- Keep `evaluate_failure` normal path delegated through `_agentic_fix_result`.
- Extend `_agentic_fix_delegate_timeout_sec`.
  - Include local verification time in each cycle budget.
  - Formula: `CI_AGENTIC_FIX_MAX_CYCLES * (CI_WAIT_TIMEOUT_SEC + 2 * SUBPROCESS_DEFAULT_TIMEOUT_SEC)`.
  - Document that the two subprocess budgets cover delegate work and local verification.
- Do not reintroduce in-process normal waterfall routing.

#### UPDATED: python/rebase.py

- Import `coder_delta_guards`.
- Capture the forbidden-path snapshot once before launching each fixer tier: `forbidden = coder_delta_guards.coder_forbidden_paths(runner, cwd=cwd)`.
- After each fixer tier launch and before accepting a resolved tier, call `coder_delta_guards.revert_forbidden_paths(runner, cwd=cwd, forbidden=forbidden)`.
  - If it reverts anything, reset conflict paths and fail closed with a redacted `Stalled` detail such as `conflict fixer touched forbidden path`.
- The snapshot is captured once per fixer tier, before `launch_fn`, so it is frozen at launch time and not re-evaluated post-mutation.
- Keep the guard independent from the user conflict handoff path.
- Preserve existing conflict marker checks and waterfall behavior.

#### UPDATED: python/test_ci_agentic_fix.py

- Add or update stubbed tests for `_run_cycle` and `main`.
- Cover first-cycle non-health behavior:
  - `cycle=1` non-health returns `first-fixer-non-health`.
- Cover later-cycle non-health behavior:
  - `cycle=2` non-health returns `waterfall-failed`.
  - `main(... --max-cycles 2)` continues and only exhausts at the cap.
- Cover passive wait fail-closed behavior:
  - `_wait_for_ci` nonzero or malformed output causes `_run_cycle` to return `ci-fix-exhausted`.
  - Emitted `STATUS` is `ci-fix-exhausted`.
  - No stale `FAILED_RUN_ID` reuse is asserted.
- Cover `ACTION=bail` from wait output:
  - Assert the delegate emits or returns `ci-fix-exhausted`.
  - Assert the detail includes the bail reason when present.
- Keep every agent launch, CI wait, and git action monkeypatched or run through fake runners.

#### UPDATED: python/test_ci_monitor.py

- Update the six direct `run_ci_fix(... ci_fix_rebase_pending=False ...)` tests.
  - Remove assertions for the deleted in-process waterfall.
  - Replace with tests that assert the defensive fail-closed result for non-pending `run_ci_fix`.
- Keep pending retry tests for `ci_fix_rebase_pending=True`.
- Add a unit test for `_agentic_fix_delegate_timeout_sec`.
  - Monkeypatch the config constants.
  - Assert the returned budget includes CI wait, delegate subprocess, and verify subprocess time per cycle.
- Replace a critical subset of skipped `evaluate_failure` tests with stubbed `_agentic_fix_result` tests.
  - Cover normal delegate routing.
  - Cover exhausted detail propagation.
  - Cover local-unfixable promotion when `FIX_ATTEMPTED=true`.
  - Cover in-progress logs deferring without launching an LLM.
- Do not unskip old tests that require the deleted in-process waterfall.

#### UPDATED: python/test_rebase.py

- Add conflict-resolution forbidden-path guard tests.
- Use monkeypatches for `coder_delta_guards.coder_forbidden_paths` and `revert_forbidden_paths`.
- Cover a successful fixer tier that also touches a forbidden path:
  - Assert `_resolve_conflicts` raises `Stalled`.
  - Assert conflict paths are reset.
  - Assert no pre-push handoff flag is written.
- Assert that the forbidden-path snapshot is captured once before `launch_fn` (pre-launch snapshot, not a post-tier recompute).
- Keep tests fake-runner based. Do not invoke real git.

#### UPDATED: python/test_checks.py

- Add only missing lint-fix waterfall coverage.
- If current Claude-first tests already cover the production path, keep them and add no duplicate.
- Ensure coverage includes:
  - Claude attempted before Codex and Cursor.
  - Codex then Cursor fallback when Claude fails.
  - All tiers failing maps to the existing dispatch-failed or main-agent-required behavior.
- Keep all coder tools monkeypatched. Do not call Claude, Codex, or Cursor.

#### UPDATED: skills/implement/references/conflict-resolution.md

- Clarify the `checkout-ours` sentence without changing the procedure.
- Make clear that `${CLAUDE_PLUGIN_ROOT}/scripts/git-checkout-ours.sh <file>` selects the upstream main side during rebase (ours = upstream/main during rebase inversion).
- Preserve the required labels: upstream (main) and feature branch commit.
- Do not add new conflict-resolution phases or reviewer behavior.

### Edge cases

- A pushed fix followed by malformed CI wait output must not silently burn cycles against the old run.
- `ACTION=bail` may contain no `BAIL_REASON`; use a stable fallback detail.
- Later-cycle non-health failures should keep retrying until the delegate cycle cap.
- Pending rebase retry must still force-push only after local verification passes.
- Forbidden-path conflict fixer edits must be reverted before stalling; snapshot is frozen before launch.
- Tests must not depend on installed external agent binaries.

### Failure modes

- If `run_ci_fix` still contains normal waterfall code, future callers may bypass the delegated CI fixer.
- If wait errors return `pushed`, parent logic may treat an unknown CI state as progress.
- If `first-fixer-non-health` appears after cycle 1, monitor routing may ask for user input too early.
- If the delegate timeout omits verify time, the parent may kill a valid delegate before it can report its own result.
- If conflict resolution accepts forbidden path edits, submodule or protected plugin metadata can be changed during rebase recovery.

### Testing strategy

Run focused tests first:

- `python3 -m pytest python/test_ci_agentic_fix.py`
- `python3 -m pytest python/test_ci_monitor.py`
- `python3 -m pytest python/test_rebase.py`
- `python3 -m pytest python/test_checks.py`

Then run required repo checks:

- `make py-lint`
- `make py-test`
- `make lint`

### Notes for implementer

- Do not add LLM calls to tests.
- Prefer monkeypatches and fake runners.
- Keep docs prose changes narrow.
- Do not update `SECURITY.md` unless implementation changes security-relevant policy beyond enforcing existing forbidden-path guards.

## Acceptance

- `_run_cycle` returns `ci-fix-exhausted` (not `pushed`) when `_wait_for_ci` errors.
- `ACTION=bail` from CI wait returns `ci-fix-exhausted` before rebase/behind/pass branches.
- All fail-closed terminal returns set `next_run_id=None`.
- `cycle > 1` non-health failure returns `waterfall-failed`, not `first-fixer-non-health`.
- `run_ci_fix` called with `ci_fix_rebase_pending=False` returns `FixResult(status="waterfall-failed")`.
- `_agentic_fix_delegate_timeout_sec()` budget includes 2x `SUBPROCESS_DEFAULT_TIMEOUT_SEC` per cycle.
- `_resolve_conflicts` calls `revert_forbidden_paths` after each fixer tier; snapshot is frozen before `launch_fn`.
- `conflict-resolution.md` clarifies that `git-checkout-ours.sh` selects the upstream main side during rebase.
- New tests pass without real LLM calls.
- `make py-lint && make py-test && make lint` pass.

review_status: complete
rounds_completed: 3
diff_lines: 380
