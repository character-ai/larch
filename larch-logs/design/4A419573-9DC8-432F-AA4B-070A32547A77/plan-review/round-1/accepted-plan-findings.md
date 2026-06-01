### FINDING_1: Existing `apply_bump` monkeypatch stubs reject new `base_remote`/`base_ref` kwargs
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-Innovation, Codex-Requirements, Codex-dyn-port-parity, Cursor-dyn-base-plumbing, Codex-dyn-base-plumbing, Cursor-dyn-scope-boundary, Codex-dyn-scope-boundary
- **Severity**: important
- **Concern**: The plan wires `rebase_and_rebump` to call `version_bump.apply_bump(..., base_remote=base_remote, base_ref=base_ref, cwd=cwd)` (e.g. `python/rebase.py` ~598), but two existing tests monkeypatch `apply_bump` with local `_apply` stubs that only accept `runner`, `new_version`, and `cwd` (`python/test_rebase.py:552-557` in `test_rebase_result_uses_apply_result_new_version`, `822-827` in `test_version_regression_guard_recomputes_target`). After that production change, those tests will raise `TypeError: unexpected keyword argument 'base_remote'` (and/or `base_ref`) before any new assertions run, so `make py-test` fails and contradicts any plan claim that existing `test_rebase.py` cases pass unchanged without edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the UPDATED python/test_rebase.py section to widen both _apply stubs (defaults or **kwargs) or document the signature change explicitly
  - From Codex-Arch: Update both existing stubs to accept base_remote and base_ref or **kwargs, and assert defaults where useful
  - From Codex-Edge: Update those stubs to accept base_remote/base_ref or **kwargs; optionally assert default origin/main where useful
  - From Codex-Pragmatic: Update those stubs to accept base_remote/base_ref or **kwargs; optionally assert default origin/main where useful
  - From Codex-Innovation: Extend the two local _apply doubles to accept base_remote and base_ref keywords, or add **_unused, as part of the planned python/test_rebase.py update
  - From Codex-Requirements: Update the existing stubs to accept base_remote/base_ref or **kwargs, and remove the “existing tests unchanged” claim
  - From Codex-dyn-port-parity: Include the two existing test stubs in python/test_rebase.py in the test update scope and let them accept base_remote/base_ref or **kwargs.
  - From Cursor-dyn-base-plumbing: Add base_remote/base_ref (or **kwargs) to both _apply stubs in the UPDATED test_rebase.py section, or document that signature change explicitly
  - From Codex-dyn-base-plumbing: Update the existing _apply stubs to accept base_remote: str = "origin" and base_ref: str = "main" or **kwargs, and optionally assert the default values where useful
  - From Cursor-dyn-scope-boundary: Add stub updates (accept base_remote/base_ref or **kwargs) to the ### UPDATED: python/test_rebase.py section and drop the unchanged-and-passing claim for those cases
  - From Codex-dyn-scope-boundary: Update the plan to include adjusting these existing stubs to accept base_remote and base_ref or **kwargs, in addition to the new base-threading tests


### FINDING_2: Planned `test_apply_bump_receives_base` can fail or expand scope via real `classify_bump`
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The planned `test_apply_bump_receives_base` (plan.txt ~41-54) may assert git traffic (no `origin`/`main` fetch/show) while leaving `classify_bump` unmocked. Real `classify_bump` always calls `git.fetch(runner, "origin", "main", ...)` (`python/version_bump.py:251`) before `apply_bump` wiring is exercised, so the test can fail on `origin/main` traffic even when `rebase_and_rebump` correctly passes `base_remote`/`base_ref` into `apply_bump`. That conflicts with the explicit non-goal to leave `classify_bump` on `origin/main` and risks pressuring implementers to change `classify_bump` in this gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Specify monkeypatch classify_bump (return PATCH + target_version like other test_rebase rebump cases) before asserting git traffic; or assert only apply_bump kwargs via a spy and keep fetch/show checks in test_apply_bump_threads_base
  - From Codex-Requirements: Constrain the assertion to apply_bump’s guard calls, or monkeypatch classify_bump so the test only verifies rebase passes base_remote/base_ref into apply_bump

