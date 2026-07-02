### OOS_1: [OUT_OF_SCOPE] Set Cursor auto-fix lane headless env (`66d2e3b2f`)
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The diff adds `agents.cursor_auth_export_env()` in `_dispatch_vendor_fix`'s Cursor branch (after `resolve_model_args`, before `subprocess.run` of `run-external-agent`) plus a focused offline regression test (`test_auto_fix_cursor_dispatch_sets_no_open_browser`). The change mutates `os.environ` before spawn without a custom `env=`, so the child inherits `NO_OPEN_BROWSER=1`; `run-external-agent` snapshots via `Ctx.from_env()` → `subprocess_env()` and propagates to the inner `cursor agent -p` spawn. Matches the established lane pattern and the implementation plan for #5797.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] chore(larch-logs) flush — intentional run-log commit, out of review scope (`aefbd2a79`)
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The `chore(larch-logs)` flush is an intentional run-log commit, not scope drift. Review scope is one production line in `python/larch/design/plan_quality.py` plus a focused regression test in `python/tests/design/test_plan_quality.py`; the larch-logs commit is out of review scope per instructions.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] `collect_results` CMD_JSON retry path may spawn without `cursor_auth_export_env`
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: `python/larch/agents/collect_results.py:443-468` — `_launch_cmd_json_retry` can spawn `run-external-agent` for cursor via `Popen(..., env=_env_without_test_hooks())` without calling `cursor_auth_export_env()` in the collector process. Review-shaped CMD_JSON is routed to `launch-review` (which exports), so this is a narrower retry path. Pre-existing relative to this diff; related to feature item 3's broader lane audit, not introduced here.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] Plan auto-fix Cursor path lacks auth preflight before spawn
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `python/larch/design/plan_quality.py:1087-1120` — The plan auto-fix Cursor path still does not run `cursor_preread_service_token()` / `cursor_auth_preflight()` before spawn, unlike `coder_runner._run_coder_cursor`. That predates this diff and is outside #5797's headless-env scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Only if auth failures in this lane become a problem; mirror the coder_runner preflight chain.

### OOS_5: [OUT_OF_SCOPE] `_auth.py` comment may overstate Cursor lane coverage
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `python/larch/agents/_auth.py:166-167` — The comment "All cursor lanes call this pre-spawn" may still be inaccurate for non-Python spawn sites (e.g. skill shell references). This PR closes the known Python gap in `plan_quality.py` but does not include the plan's full repo grep audit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Run the acceptance grep and either fix any remaining sites or narrow the comment.

### OOS_6: [OUT_OF_SCOPE] Regression test asserts env outcome but not helper invocation
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: The regression test asserts `NO_OPEN_BROWSER` in the captured spawn environment but does not assert `cursor_auth_export_env()` was called. A future one-line `os.environ["NO_OPEN_BROWSER"]="1"` refactor could pass while dropping `CURSOR_API_KEY` sanitization from the shared chokepoint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Optionally `monkeypatch` and assert the helper was invoked once; keep the env capture as the primary guard.
  - From cursor-specialist-testing: Optionally monkeypatch `cursor_auth_export_env` with a spy that records invocation, or assert both `NO_OPEN_BROWSER` and a side effect unique to the helper (e.g. key normalization) if you want stronger coupling to the shared chokepoint.

### OOS_7: [OUT_OF_SCOPE] No structural CI guard for plan acceptance grep
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The plan's acceptance grep for all `cursor agent -p` production sites is manual operator verification only; the diff adds no structural CI guard (lint, harness grep, or parameterized lane table) to prevent another missed lane.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Consider a small structural test or lint rule that enumerates known Cursor spawn call sites and requires `cursor_auth_export_env()` (or equivalent) within N lines, similar to how CI checks focus-area enums in prompt surfaces.

### OOS_8: [OUT_OF_SCOPE] Existing integration-style autofix test would not catch export removal
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `python/tests/design/test_plan_quality.py:1407-1480` — Existing integration-style autofix coverage (`test_auto_fix_dispatch_alternation_with_stub`) still routes through `LARCH_AUTOFIX_DISPATCH_SH` and would not catch removal of the pre-spawn export in real `_dispatch_vendor_fix`. That gap is why the new unit test exists; no action needed beyond keeping both tests.
- **Suggested revisions (informational for voters; coder decides)**:

