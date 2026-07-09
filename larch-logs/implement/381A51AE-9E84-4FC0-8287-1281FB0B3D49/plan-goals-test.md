## Goal
Implement issue #6685: [IMPLEMENTING] Activate `/implement` run pointer.

## Implementation Plan
## Plan

## Approach

Add the `/implement` progress pointer activation in the existing non-resume `_phase_infra` path.

Keep the change narrow:
- Use the resolved `st.run_id`.
- Call `progress activate` only when the run ID passes `progress_file.validate_run_id()` — the same validator `activate_run()` uses — not bootstrap's broader `_valid_run_id()`.
- Pass `--repo-root str(Path.cwd())`.
- Ignore the return code and stderr. This is best-effort and must not set `STEP_FAILED`.

**Why stricter validation:** `_valid_run_id()` accepts reserved names such as `current`, `.`, and `..` that `validate_run_id()` rejects. Calling `progress activate` with those IDs fails silently and leaves the prior clone `current` pointer in place, breaking the run-pointer contract on an otherwise accepted bootstrap input path.

Add a small local helper (for example `_activatable_run_id(run_id: str) -> bool`) that wraps `validate_run_id()` in a `ValueError` handler. Do not change `resolve_run_id()` or its `_valid_run_id()` acceptance rules; only gate the activation call.

Place the call after:

```python
st.run_id = st.resolve_run_id()
```

and before the Step 0 timing mark. Prefer placing it immediately after run ID resolution so ordering is clear.

## Files to modify/create

### UPDATED: python/larch/state/bootstrap.py

In `_phase_infra`, in the non-resume setup branch:
- Keep `st.run_id = st.resolve_run_id()`.
- Import `validate_run_id` from `larch.report.progress_file`.
- Add a local `_activatable_run_id(run_id: str) -> bool` helper that returns `True` only when `validate_run_id(run_id)` succeeds.
- Add a guarded best-effort call:

if _activatable_run_id(st.run_id):
    _cli("progress", "activate", "--repo-root", str(Path.cwd()), "--run-id", st.run_id)

Do not use `_valid_run_id()` for this guard.
Do not route failures through `emit_step_failed`.
Do not change resume handling, `resolve_run_id()`, or `_write_base_session_env()`.

### UPDATED: python/tests/state/test_bootstrap.py

Add focused unit coverage for `_phase_infra`:
- Explicit `--run-id` wins over setup `SESSION_ID`.
- Setup `SESSION_ID` is used as the fallback run ID.
- `progress activate` is called before `timing mark "Step 0 — preflight"`.
- A non-zero `progress activate` result does not raise, does not emit `STEP_FAILED`, and allows bootstrap to continue.
- Reserved run IDs (`current`, `.`, `..`) resolved via `--run-id` do **not** invoke `progress activate` (regression for the `validate_run_id` / `activate_run` contract).

Use monkeypatched `_cli` calls and existing `BootstrapState` patterns. Set `LARCH_CLAUDE_PID` and return success for `session write-implement-env` so pointer-env handling does not mask the progress assertions.

## Edge cases

- Invalid, empty, or reserved run IDs (`current`, `.`, `..`) must skip activation.
- Run IDs that pass `_valid_run_id()` but fail `validate_run_id()` must skip activation without calling the CLI.
- `progress activate` CLI failure must stay silent for bootstrap control flow.
- Existing resume path behavior must not change.

## Failure modes when non-trivial

- Calling activation before `resolve_run_id()` can write an empty or stale pointer.
- Using `_valid_run_id()` for the activation guard can call `progress activate` with reserved IDs, fail silently, and leave a stale `current` pointer.
- Treating activation failure as fatal can break `/implement` startup on progress-cache permission issues.
- Forgetting `Path.cwd()` can scope the pointer to the wrong repo root.

## Testing strategy

Run changed Python tests only:

```bash
python3 -m pytest python/tests/state/test_bootstrap.py

If time allows, also run the relevant Python lint for changed files:

make py-lint

## Acceptance

Run changed Python tests only:

```bash
python3 -m pytest python/tests/state/test_bootstrap.py

If time allows, also run the relevant Python lint for changed files:

make py-lint

diff_added: 105
diff_deleted: 2
mechanical_churn: false
diff_lines: 107

## Test plan
(no test plan section in plan-file)
