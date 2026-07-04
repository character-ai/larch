### FINDING_3: Fake validate must bootstrap production trailing semantics
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The publish regression's fake `plan validate` branch can still be satisfied by substring or duplicated-regex logic unless it imports the production `trailing_plan_difficulty()` implementation with a real `python/` path bootstrap, and that harness should remain test-local instead of tightening the shared fake CLI globally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the fake validate branch, bootstrap sys.path to the workspace python package root (test-supplied env var) before importing difficulty.trailing_plan_difficulty(plan_text), or delegate plan validate to the real cli.py for this test only; keep rejecting mid-document-only tiers after rewrite
  - From Cursor-Innovation: In the new test, pass an env var with the real repo `python/` parent (or invoke production `plan validate` via subprocess). In the fake CLI `plan validate` branch, import `larch.calibration.difficulty` from that path and fail when `LARCH_REQUIRE_PLAN_DIFFICULTY=1` and `not difficulty.trailing_plan_difficulty(plan_text)`.
  - From Cursor-Pragmatic: Extend `_write_difficulty_recording_cli` (or add a sibling writer used only by the new regression): in the `plan validate` branch, bootstrap repo `python/` on `sys.path` via test-set `PYTHONPATH` (same pattern as `test_design_lifecycle.py`), `from larch.calibration import difficulty`, read `--plan-file`, and fail when `not difficulty.trailing_plan_difficulty(plan_text)` while `LARCH_REQUIRE_PLAN_DIFFICULTY=1`. Remove the substring gate at line 245.
  - From Cursor-Pragmatic: Name the harness explicitly: reuse or extend `_write_difficulty_recording_cli` with `FAKE_CLI_REQUIRE_DIFFICULTY=1` for the new stranded-shape regression; keep `_write_fake_cli` unchanged for unrelated publish tests.
  - From Cursor-Requirements: In the new test only, extend the fake validate branch to import production difficulty (sys.path insert to the real plugin python tree via an env var such as LARCH_REAL_PLUGIN_ROOT, or subprocess-delegate to the real python/cli.py plan validate with the same env), and fail when trailing_plan_difficulty(plan_text) is empty under LARCH_REQUIRE_PLAN_DIFFICULTY=1.

Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

