## Proposed Design Outline

### Goals
- Fail `/design` and `/implement` entry when `git stash list` is non-empty.
- Require `/design` to start on the `main` branch (currently skipped via `--skip-branch-check`).
- Emit a stash-specific recovery hint in `PREFLIGHT_ERROR` distinct from the dirty-tree hint.

### Non-goals
- Changing `/implement`'s `<USER_PREFIX>/*` bypass for feature-branch continuation.
- Modifying `CleanTreeResult` or `_clean_tree()` return type (no composite-data refactor).
- Adding a new `git stash-check` CLI verb.

### Approach sketch
- Add `_stash_check()` helper in `admission.py` (adjacent to `_clean_tree()`): calls `git stash list` via `_run()`, returns a scalar string status.
- In `preflight_main()`, call `_stash_check()` after the clean-tree check passes; emit a stash-specific `PREFLIGHT_ERROR` hint on non-empty stash.
- Remove `"--skip-branch-check"` from `design_step0.py` line 166.
- Update the normalized error message in `bootstrap.py` + `docs/clean-main-contract.md`.
- Update tests in `test_admission.py` (new stash test cases; no change to `test_git.py` existing tests).

### Surfaces in scope
- `python/larch/state/admission.py` (new `_stash_check`, updated `preflight_main`)
- `python/larch/design/design_step0.py` (remove `--skip-branch-check`)
- `python/larch/state/bootstrap.py` (error message string)
- `docs/clean-main-contract.md`
- `python/tests/state/test_admission.py`

### Open questions
- None.
