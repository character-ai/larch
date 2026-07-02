## Goal
Implement issue #5972: [IMPLEMENTING] [BUG] #5797 residual: /design vendor auto-fix Cursor lane spawns without NO_OPEN_BROWSER=1; Cursor.app GUI popup can still fire.

## Implementation Plan
## Plan

## Approach

- `approach-synthesis` is `NO_SKETCHES`; this plan is based on direct repo inspection.
- Keep the fix narrow.
- In the Cursor branch of `_dispatch_vendor_fix`, call `agents.cursor_auth_export_env()` before launching `python/cli.py agent run-external-agent --tool cursor ... cursor agent -p`.
- Preserve the existing Codex branch, Cursor argv shape, timing behavior, and model argument handling.
- Add one regression test that exercises `_dispatch_vendor_fix(vendor="cursor", ...)` without running external tools.
- The test should prove the Cursor spawn inherits `NO_OPEN_BROWSER=1`.

## Files to modify/create

### UPDATED: python/larch/design/plan_quality.py

- In `_dispatch_vendor_fix`, Cursor branch:
  - Add `agents.cursor_auth_export_env()` before `cursor_cmd` is spawned.
  - Prefer placing it after `model_args` resolves and before `cursor_cmd` is built, so the shared pre-spawn chokepoint runs for the actual Cursor lane.
- Do not add a new env dict unless needed.
- Do not change the Codex branch.

### UPDATED: python/tests/design/test_plan_quality.py

- Add a focused unit test near the existing auto-fix dispatch tests.
- Test shape:
  - Clear `NO_OPEN_BROWSER` with `monkeypatch.delenv`.
  - Create `run_dir`, `prompt`, `design_tmpdir`, and a dummy `plugin` path.
  - Monkeypatch `plan_quality.agents.resolve_model_args` to return an object with `argv=()`.
  - Monkeypatch `plan_quality.subprocess.check_output` to return a stable timestamp.
  - Monkeypatch `plan_quality.subprocess.run`:
    - Return wrapped prompt stdout for the `cursor-wrap-prompt` call.
    - When argv contains `run-external-agent`, capture `os.environ.copy()` and return rc 0.
    - Return rc 0 for `timing record-vendor-task`.
  - Call `_dispatch_vendor_fix(vendor="cursor", ...)`.
  - Assert rc is 0.
  - Assert captured spawn env has `NO_OPEN_BROWSER == "1"`.
  - Assert the captured command still includes `cursor agent -p`.
- Keep the test offline and side-effect free outside `tmp_path`.

## Edge cases

- If `cursor-wrap-prompt` fails, behavior should stay unchanged and return 1.
- If model argument resolution fails, behavior should stay unchanged.
- Existing `CURSOR_API_KEY` trimming/removal remains owned by `cursor_auth_export_env()`.

## Failure modes

- A test that only asserts global `os.environ` after the function returns could miss a future refactor that supplies a custom `env` without `NO_OPEN_BROWSER`. Capture the environment at the mocked spawn point.
- A regression test that invokes `auto_fix_plan_commands_main` may need more scaffolding and can obscure the missing pre-spawn export. Prefer direct `_dispatch_vendor_fix` coverage.

## Testing strategy

- Run the focused test:
  - `python3 -m pytest python/tests/design/test_plan_quality.py -k no_open_browser`
- Run the relevant Python test file if practical:
  - `python3 -m pytest python/tests/design/test_plan_quality.py`
- Run lint for changed Python files if dependencies are present:
  - `make py-lint`
- Re-check Cursor spawn coverage with grep:
  - `grep -R "cursor agent -p" -n --exclude-dir='__pycache__' --exclude-dir='.pytest_cache' --exclude-dir='larch-logs' python skills agents scripts docs SECURITY.md`
  - Confirm the production Python Cursor spawn sites either call `cursor_auth_export_env()` pre-spawn or already export `NO_OPEN_BROWSER=1` in their shell context.

## Acceptance

- Run the focused test:
  - `python3 -m pytest python/tests/design/test_plan_quality.py -k no_open_browser`
- Run the relevant Python test file if practical:
  - `python3 -m pytest python/tests/design/test_plan_quality.py`
- Run lint for changed Python files if dependencies are present:
  - `make py-lint`
- Re-check Cursor spawn coverage with grep:
  - `grep -R "cursor agent -p" -n --exclude-dir='__pycache__' --exclude-dir='.pytest_cache' --exclude-dir='larch-logs' python skills agents scripts docs SECURITY.md`
  - Confirm the production Python Cursor spawn sites either call `cursor_auth_export_env()` pre-spawn or already export `NO_OPEN_BROWSER=1` in their shell context.

diff_added: 45
diff_deleted: 0
mechanical_churn: false
diff_lines: 45

## Test plan
(no test plan section in plan-file)
