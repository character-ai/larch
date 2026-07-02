## Proposed Design Outline

### Goals
- Close the #5797 gap: make the `/design` plan-autofix Cursor lane export `NO_OPEN_BROWSER=1` before spawning `cursor agent -p`, so no Composer GUI window can pop up during `plan auto-fix-commands` / `plan validator-autofix`.
- Add regression coverage that proves this lane's spawn environment carries `NO_OPEN_BROWSER=1`.
- Confirm (repo-wide) no other Cursor spawn site is missing this export, so the `_auth.py:168` "all cursor lanes" comment stays true.

### Non-goals
- No change to the codex branch of `_dispatch_vendor_fix`.
- No change to Cursor auth, trust, or sandbox posture.
- No broader refactor of `_dispatch_vendor_fix` or `cursor_auth_export_env()`.

### Approach sketch
- In `python/larch/design/plan_quality.py`, cursor branch of `_dispatch_vendor_fix`, call `agents.cursor_auth_export_env()` before building and spawning `cursor_cmd`. This mirrors the pre-spawn call already used in `_review_launcher.py`, `_ci_launcher.py`, `_drafter.py`, `coder_runner.py`, and `checks_lint_fix.py`.
- Add a regression test in `python/tests/design/test_plan_quality.py` that exercises `_dispatch_vendor_fix` on the cursor branch and asserts `NO_OPEN_BROWSER=1` is present in the spawn environment, mirroring `test_agents.py:627-632`.
- No other production file changes: a repo-wide sweep confirms every other Python Cursor-spawn site and the one Bash-embedded site (`skills/research/references/validation-phase.md`) already set this env var.

### Surfaces in scope
- `python/larch/design/plan_quality.py` (`_dispatch_vendor_fix`)
- `python/tests/design/test_plan_quality.py` (new regression test)

### Open questions
- None.
