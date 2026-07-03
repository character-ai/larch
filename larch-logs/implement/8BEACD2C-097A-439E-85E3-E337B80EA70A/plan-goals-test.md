## Goal
Implement issue #6106: [IMPLEMENTING] [BUG] /implement: architectural-guidelines note dropped on routine Step 8+ rebase.

## Implementation Plan
## Plan

## Approach

Implement the approved scoped fix.

- Add one shared helper in `ship_guidelines.py` that tries to re-pin the staged architectural-guidelines note for the current `HEAD`.
- Fall back to `_invalidate_guidelines_note(...)` only when the pin cannot be attempted or returns `False`.
- Resolve the fresh post-rebase or pre-push `HEAD` at each rebase/pending-retry caller with existing injected `git.try_rev_parse(...)` helpers.
- Pass a qualified base label, `f"{base_remote}/{base_ref}"`, so forked and upstream flows use the same diff base the rebase or pending-retry path just used.
- Keep the helper return value compatible with current refresh callbacks: return whether a warning was logged during fallback invalidation.
- Route only no-delta paths (ship_merge.py's two rebase handlers, ci_monitor.py's pending-retry callback) through the new helper. Do NOT route ci_agentic_fix.py's delta-producing push callbacks through it: a CI-fix commit changes the diff the staged assessment never covered, so unconditional invalidation there is correct, not a bug (FINDING_6).
- Remove dead `monitor.did_fixing` state and the stale invalidate branch in `ship.py`.
- Do not refactor the already-hardened PR-compose and closeout pin paths.

## Files to modify/create

### UPDATED: python/larch/implement/ship_guidelines.py

- Add `_pin_or_invalidate_guidelines_note(...)`, or a similarly named private helper.
- Parameters:
  - `implement_tmpdir: str`
  - `head_sha: str`
  - `base_ref: str`
  - `repo_root: str | None = None`
- Behavior:
  - Return `False` immediately when `implement_tmpdir` is empty.
  - If `head_sha` is non-empty, call `architectural_guidelines.pin_note_from_staged_for_current_head(...)`.
  - Return `False` when pinning succeeds.
  - Call `_invalidate_guidelines_note(implement_tmpdir)` when pinning is skipped, fails, or no `head_sha` is available.
- Do not duplicate `_pin_and_load_guidelines_note(...)` PR-body composition logic.
- Keep `_invalidate_guidelines_note(...)` as the single fallback path so drop-notice persistence stays centralized.

### UPDATED: python/larch/implement/ship_merge.py

- Add `from larch.git import git` (this module currently imports only `gh`, `push`, and `rebase` from `larch.git`; `git.try_rev_parse` is not yet available here).
- Import the new helper instead of `_invalidate_guidelines_note`.
- In `_ship_rebase_phase`, after successful `rebase.rebase_and_push(...)` and before returning:
  - Resolve `HEAD` with `git.try_rev_parse(runner, "HEAD", cwd=cwd) or ""`.
  - Call the new helper with `working.tmpdir`, the resolved head, `f"{base_remote}/{base_ref}"`, and `repo_root=cwd`.
- Apply the same change in `_ship_phase14_rebase`.
- Preserve existing state writes, counter increments, phase14 flag handling, and exception flow.

### UPDATED: python/larch/implement/ci_monitor.py

- Remove `did_fixing` from `MonitorResult`.
- Remove the `_base_result(did_fixing=...)` parameter and every `did_fixing=False` construction site.
- In `run_ci_fix(...)`, replace `_invalidate_guidelines_before_push()` with a pin-before-invalidate callback:
  - Return `False` when `ctx` is missing.
  - Resolve `HEAD` through `git.try_rev_parse(runner, "HEAD", cwd=cwd) or ""`.
  - Call the new shared helper with `ctx.tmpdir`, the resolved head, `f"{base_remote}/{base_ref}"`, and `repo_root=cwd`.
- Keep `_refresh_before_stage_push(...)` semantics unchanged. It should still run the callback before log refresh and still require log refresh after rebase or pending rebase.
- This callback only ever fires with `delta_paths=()` (the pending-retry path always calls `stage_and_push` with an empty delta tuple), so routing it through the new pin-first helper is safe and FINDING_6's concern does not apply here.

### UPDATED: python/larch/implement/ci_agentic_fix.py (comment only, no behavior change)

- Do NOT route `_invalidate_guidelines_before_ci_push` through the new shared helper (FINDING_6, accepted [SCOPE-REDUCTION]): both its call sites (~line 501, ~line 726) fire only after `stage_and_push` commits real `delta_paths` from a CI-fix agent, so the staged assessment never covered that diff and unconditional invalidation is the correct behavior here, not the bug this issue describes.
- Add a short comment on `_invalidate_guidelines_before_ci_push` recording this reasoning, so a future change does not "fix" this call site the same way as the other three and reintroduce a stale-note risk.
- No functional change to this file.

### UPDATED: python/larch/implement/ship.py

- Drop `_invalidate_guidelines_note` from imports if it is no longer used.
- Remove the dead `if monitor.did_fixing:` branch and its `fix_attempts += 1`.
- Keep `monitor.transient_rerun_attempted` handling.
- Keep `monitor.goto_rebase` handling, which now re-pins through `ship_merge.py`.

### UPDATED: python/larch/implement/ship_resume.py

- Update `_monitor_persisted_counters(...)` to remove the `monitor.did_fixing` increment.
- Keep `goto_rebase` and `transient_rerun_attempted` counter handling intact.
- Adjust type usage for the updated `MonitorResult`.

### UPDATED: python/tests/implement/test_ship.py

- Update fake `MonitorResult` construction and dict-driven monitor specs to remove `did_fixing`.
- Remove or rewrite `test_monitor_did_fixing_invalidates_guidelines_note_via_ship`.
- Add focused assertions that:
  - `_ship_rebase_phase` calls the new helper with the post-rebase `HEAD`, qualified base ref, tmpdir, and repo root.
  - `_ship_phase14_rebase` does the same.
  - successful rebase still increments `rebase_count`.
  - existing state-file and phase14 flag behavior stays unchanged.

### UPDATED: python/tests/implement/test_ci_monitor.py

- Update `MonitorResult` assertions and constructors to remove `did_fixing`.
- Add or update a `run_ci_fix(..., ci_fix_rebase_pending=True, ...)` test so the pre-push callback:
  - resolves current `HEAD`,
  - calls the new shared helper before push/log refresh,
  - passes `origin/main` or the provided remote/ref,
  - does not call raw invalidation directly.
- Keep existing assertions for pending retry, rebase, and run-log refresh behavior.

## Edge cases

- Missing `IMPLEMENT_TMPDIR`: helper returns `False`, matching current no-op invalidation behavior.
- Missing or unresolved `HEAD`: helper falls back to invalidation so stale note artifacts are not kept after a head-moving path.
- Missing staged assessment: pin returns `False`; fallback invalidates and preserves the existing drop-notice behavior.
- Fingerprint drift after rebase: pin returns `False`; fallback invalidates.
- Forked target or upstream base: callers pass `upstream/main` when their existing base fields say so.
- Warning from fallback invalidation: callback return value still lets CI-fix pre-push refresh commit the warning when current code would have done so.
- Delta-producing CI-fix push (`ci_agentic_fix.py`): continues to unconditionally invalidate; this is intentional, not an omission (FINDING_6).

## Failure modes when non-trivial

- **Silent stale note risk:** If a caller passes an old `HEAD`, the helper could pin to the wrong commit. Resolve `HEAD` after the rebase or immediately before the push callback.
- **Base-ref mismatch risk:** Passing `main` instead of `origin/main` can make live diff materialization default to `origin`. Always compose the base from the caller's `base_remote` and `base_ref`.
- **Run-log warning risk:** Changing the callback return contract can skip warning flushes. Preserve the current boolean meaning.
- **Test churn risk:** Removing `did_fixing` affects many fake monitor results. Keep this mechanical and avoid changing unrelated monitor behavior.

## Testing strategy

Run only changed-file Python tests.

- `python3 -m pytest python/tests/implement/test_ship.py`
- `python3 -m pytest python/tests/implement/test_ci_monitor.py`
- `python3 -m pytest python/tests/implement/test_ci_agentic_fix.py` (no source change expected here; confirms the existing raw-invalidate assertions still pass unchanged)

Also run targeted lint for changed Python files if dependencies are available.

- `ruff check python/larch/implement/ship_guidelines.py python/larch/implement/ship_merge.py python/larch/implement/ci_monitor.py python/larch/implement/ci_agentic_fix.py python/larch/implement/ship.py python/larch/implement/ship_resume.py python/tests/implement/test_ship.py python/tests/implement/test_ci_monitor.py`

## Acceptance criteria

- Every no-delta call site (ship_merge.py's two rebase handlers, ci_monitor.py's pending-retry callback) attempts the shared pin helper before falling back to invalidate.
- ci_agentic_fix.py's delta-producing push callbacks continue to unconditionally invalidate by design (FINDING_6); this is a confirmed-correct no-op, not an oversight.
- Raw `_invalidate_guidelines_note(...)` remains available as the helper's fallback path, as the intentional direct call for `ci_agentic_fix.py`'s push callbacks, and for existing direct fallback-behavior tests.
- `MonitorResult` no longer exposes `did_fixing`.
- The dead ship loop branch is gone.
- Existing merge, rebase, CI-fix, and pending-retry tests still pass after expected fixture updates.

confidence: high

## Acceptance

Run only changed-file Python tests.

- `python3 -m pytest python/tests/implement/test_ship.py`
- `python3 -m pytest python/tests/implement/test_ci_monitor.py`
- `python3 -m pytest python/tests/implement/test_ci_agentic_fix.py` (no source change expected here; confirms the existing raw-invalidate assertions still pass unchanged)

Also run targeted lint for changed Python files if dependencies are available.

- `ruff check python/larch/implement/ship_guidelines.py python/larch/implement/ship_merge.py python/larch/implement/ci_monitor.py python/larch/implement/ci_agentic_fix.py python/larch/implement/ship.py python/larch/implement/ship_resume.py python/tests/implement/test_ship.py python/tests/implement/test_ci_monitor.py`

diff_added: 180
diff_deleted: 120
mechanical_churn: true
diff_lines: 300

## Test plan
(no test plan section in plan-file)
